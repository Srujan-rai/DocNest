document.addEventListener('DOMContentLoaded', () => {
    // Get all clickable main items
    const mainItems = document.querySelectorAll('.main-item');
    // Get all clickable sub items
    const subItems = document.querySelectorAll('.sub-item');

    // Add click listener for Main Points
    mainItems.forEach(item => {
        item.addEventListener('click', (event) => {
            // Find the closest parent 'li'
            const parentLi = event.target.closest('li');
            if (!parentLi) return; // Should not happen, but safety check

            // Find the sub-list directly inside this 'li'
            const subList = parentLi.querySelector(':scope > .sub-list'); // ':scope >' ensures it's a direct child

            if (subList) {
                // Toggle the 'visible' class on the sub-list
                subList.classList.toggle('visible');
                clickedItem.classList.toggle('active', subList.classList.contains('visible'));

                // Optional: Add an indicator (e.g., change text or add an arrow)
                // event.target.classList.toggle('active'); // Example class for styling
            }
        });
    });

    // Add click listener for Sub Points
    subItems.forEach(item => {
        item.addEventListener('click', (event) => {
            // Stop the click from bubbling up to the main item's listener
            event.stopPropagation();

            // Find the closest parent 'li'
            const parentLi = event.target.closest('li');
            if (!parentLi) return;

            // Find the table container directly inside this 'li'
            const tableContainer = parentLi.querySelector(':scope > .table-container');

            if (tableContainer) {
                // Toggle the 'visible' class on the table container
                tableContainer.classList.toggle('visible');
                 // Optional: Add an indicator
                // event.target.classList.toggle('active'); // Example class for styling
            }
        });
    });
});