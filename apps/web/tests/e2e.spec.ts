import { expect, test } from "@playwright/test";

async function login(page: any, username: string) {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill("Password@123");
  await Promise.all([
    page.waitForURL((url: URL) => !url.pathname.includes("/login"), { timeout: 15000 }),
    page.getByRole("button", { name: "Sign in" }).click()
  ]);
}

test("auditor menu visibility and action plan creation entry", async ({ page }) => {
  await login(page, "auditoruser1");
  await expect(page.getByRole("link", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Action Plans" })).toBeVisible();
  await page.goto("/action-plans");
  await expect(page.getByRole("link", { name: "New Action Plan" })).toBeVisible();
});

test("auditee menu visibility and forbidden direct URL access", async ({ page }) => {
  await login(page, "auditeeuser1");
  await expect(page.getByText("Dashboard")).not.toBeVisible();
  await page.goto("/dashboard");
  await expect(page.getByText("outside your role boundary")).toBeVisible();
});

test("reports export actions are available", async ({ page }) => {
  await login(page, "auditoruser1");
  await page.goto("/reports");
  await expect(page.getByRole("button", { name: "Export Excel" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export PDF" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete" })).toHaveCount(0);
});

test("delete controls show only on editable tables", async ({ page }) => {
  await login(page, "auditoruser1");
  await page.goto("/action-plans");
  await expect(page.getByRole("button", { name: "Delete" }).first()).toBeVisible();
});

test("auditor sees edit and delete on editable master rows", async ({ page }) => {
  await login(page, "auditoruser1");
  await page.goto("/masters/countries");
  await expect(page.getByRole("button", { name: "Edit" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete" }).first()).toBeVisible();
});

test("auditee sees no generic edit or delete controls", async ({ page }) => {
  await login(page, "auditeeuser1");
  await page.goto("/masters/countries");
  await expect(page.getByRole("button", { name: "Edit" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Delete" })).toHaveCount(0);
  await page.goto("/action-plans");
  await expect(page.getByRole("link", { name: "Add/Edit Remarks" }).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Delete" })).toHaveCount(0);
});

test("activity logs remain non deletable", async ({ page }) => {
  await login(page, "superadmin");
  await page.goto("/admin/activity-logs");
  await expect(page.getByRole("button", { name: "Delete" })).toHaveCount(0);
});

test("super admin can access role administration", async ({ page }) => {
  await login(page, "superadmin");
  await page.goto("/admin/roles");
  await expect(page.getByText("Role Administration")).toBeVisible();
  await expect(page.getByRole("button", { name: "New Role" })).toBeVisible();
});

test("phase one master import controls are scoped to approved tables", async ({ page }) => {
  await login(page, "auditoruser1");
  await page.goto("/masters/countries");
  await expect(page.getByText("Excel Import")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download Template" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Validate" })).toBeVisible();

  await page.goto("/masters/states");
  await expect(page.getByText("Excel Import")).toBeVisible();
  await expect(page.getByRole("button", { name: "Download Template" })).toBeVisible();

  await page.goto("/masters/companies");
  await expect(page.getByText("Excel Import")).toHaveCount(0);
});
