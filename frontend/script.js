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

document.addEventListener("DOMContentLoaded", () => {
    const tables = document.querySelectorAll("table[data-sheet-url]");
  
    tables.forEach((table) => {
      const url = table.dataset.sheetUrl;
      if (!url) return;
  
      fetch(url)
        .then((response) => {
          if (!response.ok) throw new Error(`Failed to fetch ${url}`);
          return response.text();
        })
        .then((csvText) => {
          const rows = csvText
            .trim()
            .split("\n")
            .map((row) => row.split(","));
  
          renderTable(table, rows);
        })
        .catch((err) => {
          table.innerHTML = `<tbody><tr><td colspan="99" style="color:red;">${err.message}</td></tr></tbody>`;
          console.error(err);
        });
    });
  
    function renderTable(table, rows) {
      if (!rows.length) return;
  
      // Clear existing table content
      table.innerHTML = "";
  
      const thead = document.createElement("thead");
      const headRow = document.createElement("tr");
      rows[0].forEach((cell) => {
        const th = document.createElement("th");
        th.textContent = cell.trim();
        headRow.appendChild(th);
      });
      thead.appendChild(headRow);
      table.appendChild(thead);
  
      const tbody = document.createElement("tbody");
      rows.slice(1).forEach((row) => {
        const tr = document.createElement("tr");
        row.forEach((cell, index) => {
          const td = document.createElement("td");
          if (
            rows[0][index].toLowerCase().includes("link") &&
            cell.trim().startsWith("http")
          ) {
            const a = document.createElement("a");
            a.href = cell.trim();
            a.textContent = "Open";
            a.target = "_blank";
            td.appendChild(a);
          } else {
            td.textContent = cell.trim();
          }
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);
    }
  });