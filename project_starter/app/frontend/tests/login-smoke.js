// Real demo directory/login integration, without modifying the seeded balances.
async page => {
  const check = (condition, message) => { if (!condition) throw new Error(message) }
  await page.goto('http://127.0.0.1:5273')
  await page.evaluate(() => sessionStorage.removeItem('saving-streak-starter-email'))
  await page.reload()
  await page.getByRole('heading', { name: 'Sign in', exact: true }).waitFor()
  await page.getByRole('button', { name: 'Continue as Anke Peeters', exact: true }).waitFor()
  check(await page.getByRole('button', { name: /^Continue as / }).count() === 3, 'Three demo choices must load')
  await page.getByRole('textbox', { name: 'Email address' }).fill('unknown@example.com')
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await page.getByRole('alert').filter({ hasText: 'Choose a demo profile' }).waitFor()
  check(await page.getByRole('navigation').count() === 0, 'Unknown email must not enter the dashboard')
  for (const [name, first, email] of [['Anke Peeters', 'Anke', 'anke@example.com'], ['Bram De Vos', 'Bram', 'bram@example.com'], ['Lina Janssens', 'Lina', 'lina@example.com']]) {
    await page.getByRole('button', { name: `Continue as ${name}`, exact: true }).click()
    await page.getByRole('heading', { name: `Hello, ${first}.`, exact: true }).waitFor()
    await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent !== '—')
    const before = await page.locator('.stats strong').allTextContents()
    check(await page.getByRole('textbox', { name: 'Customer', exact: true }).count() === 0, 'Raw customer IDs should not be shown')
    await page.reload()
    await page.getByRole('heading', { name: `Hello, ${first}.`, exact: true }).waitFor()
    await page.waitForFunction(() => document.querySelector('.stats strong')?.textContent !== '—')
    check(JSON.stringify(await page.locator('.stats strong').allTextContents()) === JSON.stringify(before), 'Session restore must preserve balances')
    await page.getByRole('button', { name: 'Sign out', exact: true }).click()
    await page.getByRole('heading', { name: 'Sign in', exact: true }).waitFor()
    check(await page.evaluate(() => sessionStorage.getItem('saving-streak-starter-email')) === null, 'Sign out must clear remembered email')
    await page.getByRole('textbox', { name: 'Email address' }).fill(` ${email.toUpperCase()} `)
    await page.getByRole('button', { name: 'Sign in', exact: true }).click()
    await page.getByRole('heading', { name: `Hello, ${first}.`, exact: true }).waitFor()
    await page.getByRole('button', { name: 'Sign out', exact: true }).click()
  }
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 900 })
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Login overflows at ${width}px`)
    check(/for\s+good/.test(await page.getByRole('heading', { level: 1 }).innerText()), 'Login headline must preserve word spacing')
  }
  return { passed: true, checks: ['real demo directory', 'unknown email', 'three demo logins', 'email normalization', 'session restore', 'sign out', 'desktop/mobile login'] }
}
