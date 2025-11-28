
// Handle the confirmation and application of changes
async function applyChanges() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const changes = JSON.parse(decodeURIComponent(urlParams.get('changes')));
        
        const response = await fetch('/journals/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(changes)
        });
        
        if (!response.ok) {
            throw new Error('Failed to apply changes');
        }
        
        window.location.href = '/journals?success=true';
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to apply changes. Please try again.');
    }
}

// Handle mapping form submission
document.addEventListener('DOMContentLoaded', function() {
    const mappingForm = document.getElementById('mapping-form');
    if (mappingForm) {
        mappingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(mappingForm);
            const mappingData = {
                description_pattern: formData.get('description_pattern'),
                account_id: formData.get('account_id')
            };
            
            try {
                const response = await fetch('/mapping', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(mappingData)
                });
                
                if (!response.ok) {
                    throw new Error('Failed to save mapping');
                }
                
                loadCurrentMappings();
                mappingForm.reset();
            } catch (error) {
                console.error('Error:', error);
                alert('Failed to save mapping. Please try again.');
            }
        });
    }
});

// Load and display current mappings
async function loadCurrentMappings() {
    try {
        const response = await fetch('/mapping');
        if (!response.ok) {
            throw new Error('Failed to load mappings');
        }
        
        const mappings = await response.json();
        const mappingsContainer = document.getElementById('current-mappings');
        
        mappingsContainer.innerHTML = mappings.map(mapping => `
            <div class="flex justify-between items-center py-3 border-b">
                <div>
                    <p class="text-sm font-medium text-gray-900">${mapping.description_pattern}</p>
                    <p class="text-sm text-gray-500">${mapping.account_name}</p>
                </div>
                <button onclick="deleteMapping('${mapping.id}')" class="text-red-600 hover:text-red-900">
                    Delete
                </button>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to load mappings. Please refresh the page.');
    }
}