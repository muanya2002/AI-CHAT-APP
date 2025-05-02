// cypress/e2e/frontend.cy.js
describe('Frontend Tests', () => {
    beforeEach(() => {
      // Visit your application's URL
      // Replace with the URL where your Python backend serves your frontend
      cy.visit('http://localhost:8080');
    });
  
    it('loads the homepage successfully', () => {
      // Test that main elements are visible
      cy.get('header').should('be.visible');
      cy.get('footer').should('be.visible');
    });
  
    it('has working navigation', () => {
      // Test navigation links (adjust selectors to match your HTML)
      cy.get('nav a').contains('login').click();
      cy.url().should('include', '/login');
    });
  
  });