// Run with Playwright CLI's `run-code --filename` against the running starter.
// Use the isolated fixture API and frontend at port 5274; restart the fixture for each run.
async (page) => {
  const check = (condition, message) => { if (!condition) throw new Error(message) }
  const customer = 'ui-smoke'
  const nav = (name) => page.getByRole('navigation').getByRole('button', { name, exact: true })
  const form = (name) => page.locator('form').filter({ has: page.getByRole('heading', { name, exact: true }) })
  const stats = () => page.locator('.stats strong').allTextContents()
  const errors = []
  const onError = error => errors.push(error.message)
  page.on('pageerror', onError)
  await page.setViewportSize({ width: 1200, height: 900 })
  // Isolated identities for mutation tests; real demo login is covered separately.
  const loginRoute = async route => {
    const id = route.request().postDataJSON().email.split('@')[0]
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      id, name: 'Smoke Tester', email: `${id}@smoke.example`, initials: 'ST',
      account_id: `savings-${id}`, account_name: 'Everyday savings', goal: 'Test account',
    }) })
  }
  await page.route('**/api/demo/session', loginRoute)
  const signInAs = async id => {
    const signOut = page.getByRole('button', { name: 'Sign out', exact: true })
    if (await signOut.isVisible()) await signOut.click()
    await page.getByRole('textbox', { name: 'Email address', exact: true }).fill(`${id}@smoke.example`)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await page.getByRole('navigation').waitFor()
  }
  await page.goto('http://127.0.0.1:5274')
  await page.evaluate(() => sessionStorage.removeItem('saving-streak-starter-email'))
  await page.reload()
  await signInAs(customer)
  try {
    check(JSON.stringify(await page.getByRole('navigation').getByRole('button').allTextContents()) ===
      JSON.stringify(['Overview', 'Move money', 'Rewards', 'History']), 'Only starter navigation should exist')
    await nav('Move money').click()
    await page.locator('.active-account strong').filter({ hasText: '€0.00' }).waitFor()
    check(await page.locator('.active-account').innerText().then(text => text.includes('savings-ui-smoke')), 'Money screen must identify the active account')
    check(await form('Withdraw from savings').getByRole('button', { name: 'Withdraw', exact: true }).isDisabled(), 'Empty savings cannot be withdrawn')
    const deposit = form('Add to savings')
    const depositAmount = deposit.getByRole('spinbutton', { name: 'Amount (€)', exact: true })
    for (const invalid of ['2500.01', '-1', '0', '0.001']) {
      await depositAmount.fill(invalid)
      check(await depositAmount.evaluate(el => !el.checkValidity()), `Deposit ${invalid} should be invalid`)
    }
    await depositAmount.fill('150.99')
    await nav('Overview').click()
    await nav('Move money').click()
    check(await deposit.getByRole('spinbutton', { name: 'Amount (€)', exact: true }).inputValue() === '150.99', 'Form values must survive navigation')
    // The transfer commits but its response is lost. Retrying must not move money twice.
    const droppedResponse = async route => { await route.fetch(); await route.abort('failed') }
    await page.route('**/api/demo/transfers', droppedResponse)
    try {
      await deposit.getByRole('button', { name: 'Deposit', exact: true }).click()
      await page.getByRole('alert').waitFor()
      await page.waitForFunction(() => document.querySelector('#deposit-limit strong')?.textContent === '€2,349.01')
    } finally {
      await page.unroute('**/api/demo/transfers', droppedResponse)
    }
    await deposit.getByRole('button', { name: 'Deposit', exact: true }).click()
    await page.getByRole('status').filter({ hasText: 'Transfer already recorded' }).waitFor()
    await nav('Overview').click()
    await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent === '150')
    check((await stats())[1] === '€150.99', 'Deposit must update the money balance')
    check((await stats())[2] === '€2,349.01', 'Deposit must reduce available funding')
    check(await page.locator('.total-balance strong').innerText() === '€2,500.00', 'Transfer must preserve total money')
    check(await page.locator('.savings-stat').innerText().then(text => text.includes('savings-ui-smoke')), 'Overview must identify the active account')

    await nav('Move money').click()
    const withdrawal = form('Withdraw from savings')
    const withdrawalAmount = withdrawal.getByRole('spinbutton', { name: 'Amount (€)', exact: true })
    await withdrawalAmount.fill('151')
    check(await withdrawalAmount.evaluate(el => !el.checkValidity()), 'Withdrawal above savings must be invalid')
    await withdrawalAmount.fill('5.00')
    await withdrawal.getByRole('button', { name: 'Withdraw', exact: true }).click()
    await page.getByRole('status').filter({ hasText: 'Withdrawal recorded' }).waitFor()
    await nav('Overview').click()
    await page.waitForFunction(() => document.querySelectorAll('.stats strong')[1]?.textContent === '€145.99')
    check((await stats())[0] === '150', 'Withdrawal must preserve already earned base points')
    check((await stats())[2] === '€2,354.01', 'Withdrawal must return money to spending')
    check(await page.locator('.total-balance strong').innerText() === '€2,500.00', 'Withdrawal must preserve total money')
    await page.reload()
    await page.waitForFunction(() => document.querySelector('.spending-stat strong')?.textContent === '€2,354.01')

    await nav('Rewards').click()
    const claim = page.getByRole('row').filter({ hasText: 'Charity' }).getByRole('button', { name: 'Claim', exact: true })
    await claim.click()
    await page.getByRole('dialog').waitFor()
    check(await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).evaluate(el => el === document.activeElement), 'Cancel should receive initial dialog focus')
    await page.keyboard.press('Escape')
    await page.getByRole('dialog').waitFor({ state: 'detached' })
    check(await claim.evaluate(el => el === document.activeElement), 'Escape must restore focus to the selected reward')
    await claim.click()
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click()
    await page.getByRole('dialog').waitFor({ state: 'detached' })
    await nav('Overview').click()
    check((await stats())[0] === '150', 'Cancel and Escape must not spend any points')
    await nav('Rewards').click()
    // Hold confirmation in flight to inspect the busy state and duplicate-click guard.
    let releaseClaim
    let claimRequests = 0
    const claimGate = new Promise(resolve => { releaseClaim = resolve })
    const claimRoute = async route => {
      claimRequests++
      await claimGate
      await route.continue()
    }
    await page.route('**/api/claims', claimRoute)
    try {
      await claim.click()
      await page.getByRole('dialog').getByRole('button', { name: 'Confirm claim' }).click()
      await page.getByRole('button', { name: 'Claiming…', exact: true }).waitFor()
      check(await page.getByRole('button', { name: 'Claiming…', exact: true }).isDisabled(), 'Confirmation must be disabled in flight')
      check(await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).isDisabled(), 'Cancellation must be disabled during confirmation')
      await page.keyboard.press('Escape')
      check(await page.getByRole('dialog').isVisible(), 'Escape must not dismiss a claim in flight')
      releaseClaim()
      await page.getByRole('status').filter({ hasText: 'Voucher issued' }).waitFor()
      check(claimRequests === 1, 'Only one claim request should be sent')
    } finally {
      releaseClaim()
      await page.unroute('**/api/claims', claimRoute)
    }
    await page.getByRole('status').filter({ hasText: 'Voucher issued' }).waitFor()
    await page.locator('.vouchers tbody tr').waitFor()
    check(await page.locator('.vouchers tbody tr').count() === 1, 'One confirmation must issue one voucher')
    await nav('Overview').click()
    await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent === '140')

    // Hold a new customer's reads, then fail them. Old data must stay hidden.
    const nextCustomer = `${customer}-empty`
    const pattern = `**/api/customers/${nextCustomer}/**`
    let release
    const gate = new Promise(resolve => { release = resolve })
    const intercept = async route => {
      await gate
      await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'Temporary test outage' }) })
    }
    await page.route(pattern, intercept)
    try {
      await signInAs(nextCustomer)
      await page.getByRole('status').filter({ hasText: 'Loading' }).waitFor()
      check((await stats()).every(value => value === '—'), 'A pending customer read must hide the previous customer')
      await nav('Rewards').click()
      check(await page.locator('.vouchers tbody tr').count() === 0, 'Old vouchers must be hidden while loading')
      await nav('History').click()
      check(await page.locator('.history tbody tr').count() === 0, 'Old history must be hidden while loading')
      await nav('Overview').click()
      check(await page.locator('.deposit-lots tbody tr').count() === 0, 'Old deposit lots must be hidden while loading')
      release()
      await page.getByRole('alert').filter({ hasText: 'Temporary test outage' }).waitFor()
      check((await stats()).every(value => value === '—'), 'A failed customer read must keep old data hidden')
    } finally {
      release()
      await page.unroute(pattern, intercept)
    }
    await page.getByRole('button', { name: 'Retry', exact: true }).click()
    await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent === '0')
    check((await stats())[1] === '€0.00', 'Retry should load the new customer')

    // An older response that finishes after the newest read cannot repaint it.
    const lateCustomer = `${customer}-late`
    const latePattern = `**/api/customers/${lateCustomer}/points/balance`
    let releaseLate, markStarted, markHandled
    const lateGate = new Promise(resolve => { releaseLate = resolve })
    const lateStarted = new Promise(resolve => { markStarted = resolve })
    const lateHandled = new Promise(resolve => { markHandled = resolve })
    const lateRoute = async route => {
      markStarted()
      await lateGate
      try {
        await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ balance: 999 }) })
      } finally { markHandled() }
    }
    await page.route(latePattern, lateRoute)
    try {
      await signInAs(lateCustomer)
      await lateStarted
      await signInAs(nextCustomer)
      await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent === '0')
      releaseLate()
      await lateHandled
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))))
      check((await stats())[0] === '0', 'A superseded response must not overwrite the current customer')
      check(await page.getByRole('alert').count() === 0, 'A superseded request must not publish an error')
    } finally {
      releaseLate()
      await page.unroute(latePattern, lateRoute)
    }

    await nav('Rewards').click()
    await claim.click()
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm claim' }).click()
    await page.getByRole('alert').waitFor()
    await page.getByRole('dialog').waitFor({ state: 'detached' })
    check(await page.locator('.vouchers tbody tr').count() === 0, 'Refused claim must issue no voucher')

    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 })
      for (const tab of ['Overview', 'Move money', 'Rewards', 'History']) {
        await nav(tab).click()
        check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${tab} overflows at ${width}px`)
        if (tab === 'Rewards') check(await page.locator('.rewards .table-scroll').evaluate(el => el.scrollWidth <= el.clientWidth), `Reward actions require horizontal scrolling at ${width}px`)
      }
    }
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await nav('Overview').click()
    check(await page.locator('.stat').first().evaluate(el => parseFloat(getComputedStyle(el).animationDuration) < 0.01), 'Reduced motion must suppress entrance animations')
    check(errors.length === 0, `Browser errors: ${errors.join('; ')}`)
    return { passed: true, customer, checks: ['starter navigation/form persistence', 'funded deposit/withdrawal and limits', 'total and active account', 'balance persistence', 'lost-response retry', 'claim cancel/Escape/focus/busy/confirm/refusal', 'pending/failed/superseded customer', 'retry', '320/390px layouts and reward actions', 'reduced motion', 'no page errors'] }
  } finally {
    page.off('pageerror', onError)
    await page.unroute('**/api/demo/session', loginRoute)
    await page.emulateMedia({ reducedMotion: 'no-preference' })
  }
}
