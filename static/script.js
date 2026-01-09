

// backend server IP
const APIlink = 'https://192.168.0.49:5000/api';

// Edit mode

// Track whether edit mode is currently active
let editMode = false;
const editModeToggle = document.getElementById('edit-mode-toggle');

// Toggle edit mode when button is clicked
editModeToggle.addEventListener('click', () => {
    editMode = !editMode;
    const checkColumns = document.querySelectorAll('.edit-checkbox-col');

    //if edit mode on
    if (editMode) {
        document.getElementById('passcodes-table').classList.add('edit-mode');
        editModeToggle.classList.add('active');
        editModeToggle.textContent = 'Disable Edit Mode';
        checkColumns.forEach(col => col.style.display = 'table-cell');
        //if edit mode off
    } else {
        document.getElementById('passcodes-table').classList.remove('edit-mode');
        editModeToggle.classList.remove('active');
        editModeToggle.textContent = 'Enable Edit Mode';
        checkColumns.forEach(col => col.style.display = 'none');
    }
});

//Inline editing

function editingMode() {
    const editableCells = document.querySelectorAll('#passcodes-list td.editable-cell'); //find all editable cells

    editableCells.forEach(cell => { //double click event
        cell.addEventListener('dblclick', function () {
            if (!editMode) return;

            const currentValue = this.textContent;      //input field setup
            const input = document.createElement('input');
            input.type = 'text';
            input.value = currentValue;
            input.style.width = '100%';
            this.textContent = '';
            this.appendChild(input);
            input.focus();
            //detecting when user exits doube click
            input.addEventListener('blur', function () {
                const newValue = this.value;
                const td = this.parentNode;
                const row = td.parentNode;
                const allCells = Array.from(row.cells);
                const cellIndex = allCells.indexOf(td);

                //  Get the passcode ID from the checkbox in the first cell
                const passcodeId = row.querySelector('.select-passcode')?.getAttribute('data-id');

                td.textContent = newValue;

                if (newValue !== currentValue && passcodeId) {
                    let fieldToUpdate;
                    // finding which field should be updated based on which column was edited
                    switch (cellIndex) {
                        case 1: fieldToUpdate = 'name'; break;
                        case 3: fieldToUpdate = 'passcode'; break;
                        default: return;
                    }
                    console.log('Updating passcode:', {
                        id: passcodeId,
                        field: fieldToUpdate,
                        newValue: newValue
                    });
                    //building the json payload
                    fetch(`${APIlink}/passcodes/${passcodeId}`, {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            [fieldToUpdate]: newValue
                        })
                    })
                        .then(response => response.json())
                        .then(result => {
                            if (result.success) {
                                console.log(`Updated ${fieldToUpdate} for ID ${passcodeId}`);
                            } else {
                                console.log(`fail ${result.message}`);
                                td.textContent = currentValue; // revert back to original value
                            }
                        })
                        .catch(error => {
                            console.error('Fetch error:', error);
                            td.textContent = currentValue; // revert back to original value
                        });
                }
            });
        });
    });
}

//date and time formatting
function formatDateTime(dateTimeString) {
    if (!dateTimeString) return 'Never';

    const date = new Date(dateTimeString);

    // Format time in 24-hour format
    const time = date.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });

    // Format date as DD/MM/YYYY
    const dateStr = date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
    });

    // Combine with time first, then date
    return `${time} ${dateStr}`;
}

async function loadPasscodes() {
    document.getElementById('passcode-error').textContent = ''; //clear passcode display message by default

    try {
        // Fetch passcodes from API
        const response = await fetch(`${APIlink}/passcodes`); //wait for response
        const passcodes = await response.json();

        // Sort passcodes by ID in ascending order
        passcodes.sort((a, b) => a.id - b.id);

        console.log('Fetched passcodes:', passcodes); //debugging

        // Clear existing table content
        const passcodesList = document.getElementById('passcodes-list');
        passcodesList.innerHTML = '';

        // Add each passcode as a table row
        passcodes.forEach(passcode => {
            console.log('Processing passcode:', passcode);  // Debug log

            const row = document.createElement('tr');

            //name
            //id
            // user passcode
            // last access
            // date created

            row.innerHTML = `
                <td class="edit-checkbox-col" style="display: none;">
                <input type="checkbox" class="select-passcode" data-id="${passcode.id}">
                </td>
                <td class="editable-cell">${passcode.name}</td> 
                <td>${passcode.id}</td>
                <td class="editable-cell">${passcode.passcode}</td>
                <td>${formatDateTime(passcode.lastAccess)}</td>
                <td>${formatDateTime(passcode.created)}</td>
            `;
            passcodesList.appendChild(row);
        });

        // Enable inline editing for editable cells
        editingMode();

    } catch (error) {
        console.error('passcodde not loading', error);
        const errorMessage = document.getElementById('passcode-error');
        errorMessage.textContent = 'Failed to load/refresh passcodes. Try reloading or check server is running...';
    }
}

//user deleter
document.getElementById('delete-selected').addEventListener('click', async () => {
    const selectedBoxes = document.querySelectorAll('.select-passcode:checked');
    const idDelete = Array.from(selectedBoxes).map(cb => cb.getAttribute('data-id'));
//error handling
    if (idDelete.length === 0) {
        alert('select at least one passcode to delete');
        return;
    }
//asks for confirmation
    if (!confirm(`Delete ${idDelete .length} selected passcodes?`)) return;

    for (let id of idDelete) {
        try {
            await fetch(`${APIlink}/passcodes/${id}`, { method: 'DELETE' }); //delete request to backend server

        } catch (deleteError) {
            console.error('check python script', deleteError);
        }
    }
//reload
    loadPasscodes(); // Refresh list
});

function autoRefresh() {
    setInterval(loadPasscodes, 60000); // Refresh every minute
}

// event listeners

// Main initialization when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Passcode Management
    loadPasscodes();
    autoRefresh();

    // Set up event listeners for passcode management
    document.getElementById('refresh-btn').addEventListener('click', loadPasscodes);

});