import { expect, type Page, test } from "@playwright/test"
import { createUserWithRole } from "./utils/adminApi"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

const sidebarLink = (page: Page, name: string) =>
  page.getByRole("link", { name, exact: true })

test.describe("Manager", () => {
  const email = randomEmail()
  const password = randomPassword()

  test.beforeAll(async () => {
    await createUserWithRole({ email, password, role: "manager" })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
  })

  test("sees Users and Metrics in the sidebar", async ({ page }) => {
    await expect(sidebarLink(page, "Users")).toBeVisible()
    await expect(sidebarLink(page, "Metrics")).toBeVisible()
  })

  test("has a read-only users page", async ({ page }) => {
    await page.goto("/admin")

    await expect(page.getByRole("row").filter({ hasText: email })).toBeVisible()
    await expect(page.getByRole("button", { name: "Add User" })).toHaveCount(0)
    await expect(page.locator("tbody").getByRole("button")).toHaveCount(0)
  })

  test("can open the metrics page", async ({ page }) => {
    await page.goto("/metrics")

    await expect(page.getByRole("heading", { name: "Metrics" })).toBeVisible()
    await expect(page.getByText("Total users")).toBeVisible()
  })
})

test.describe("Member", () => {
  const email = randomEmail()
  const password = randomPassword()

  test.beforeAll(async () => {
    await createUser({ email, password })
  })

  test.beforeEach(async ({ page }) => {
    await logInUser(page, email, password)
  })

  test("sees neither Users nor Metrics in the sidebar", async ({ page }) => {
    await expect(sidebarLink(page, "Items")).toBeVisible()
    await expect(sidebarLink(page, "Users")).toHaveCount(0)
    await expect(sidebarLink(page, "Metrics")).toHaveCount(0)
  })

  test("opening /metrics directly shows access denied and stays logged in", async ({
    page,
  }) => {
    await page.goto("/metrics")

    await expect(page.getByTestId("access-denied")).toBeVisible()
    await expect(page).toHaveURL(/\/metrics$/)
  })
})
