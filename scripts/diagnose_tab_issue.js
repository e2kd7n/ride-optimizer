// Diagnostic script to check Long Rides tab visibility
// Run this in browser console after clicking Long Rides tab

console.log('=== LONG RIDES TAB DIAGNOSTIC ===');

const tabPane = document.getElementById('longrides');
if (!tabPane) {
    console.error('❌ Tab pane #longrides not found!');
} else {
    console.log('✅ Tab pane found');
    console.log('Classes:', tabPane.className);
    console.log('Display:', window.getComputedStyle(tabPane).display);
    console.log('Visibility:', window.getComputedStyle(tabPane).visibility);
    console.log('Opacity:', window.getComputedStyle(tabPane).opacity);
    console.log('Height:', window.getComputedStyle(tabPane).height);
    console.log('Has "show" class:', tabPane.classList.contains('show'));
    console.log('Has "active" class:', tabPane.classList.contains('active'));
    console.log('Has "fade" class:', tabPane.classList.contains('fade'));
}

const tabButton = document.getElementById('longrides-tab');
if (!tabButton) {
    console.error('❌ Tab button #longrides-tab not found!');
} else {
    console.log('✅ Tab button found');
    console.log('Button classes:', tabButton.className);
    console.log('Button aria-selected:', tabButton.getAttribute('aria-selected'));
}

console.log('=== END DIAGNOSTIC ===');

// Made with Bob
