/// <reference types="cypress" />

// Custom commands for Research Agent E2E tests

declare global {
  namespace Cypress {
    interface Chainable {
      /** Log in with test credentials via Supabase */
      login(email?: string, password?: string): Chainable<void>;
    }
  }
}

// Login command - uses the login page UI
Cypress.Commands.add('login', (email?: string, password?: string) => {
  const testEmail = email || Cypress.env('TEST_USER_EMAIL') || 'test@example.com';
  const testPassword = password || Cypress.env('TEST_USER_PASSWORD') || 'testpassword123';

  cy.visit('/login');
  cy.get('input[type="email"]').type(testEmail);

  // Click "Use password" toggle if it exists
  cy.get('body').then(($body) => {
    if ($body.find('[data-testid="use-password-toggle"]').length > 0) {
      cy.get('[data-testid="use-password-toggle"]').click();
    }
  });

  cy.get('input[type="password"]').type(testPassword);
  cy.get('button[type="submit"]').click();

  // Wait for redirect to dashboard
  cy.url().should('include', '/dashboard', { timeout: 15000 });
});

export {};
