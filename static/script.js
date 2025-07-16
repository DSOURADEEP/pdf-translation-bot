document.addEventListener('DOMContentLoaded', function() {
    // Single file upload
    const fileInput = document.getElementById('file-input');
    if (fileInput) {
        fileInput.addEventListener('change', handleSingleUpload);
    }

    // Batch file upload
    const batchFileInput = document.getElementById('batch-file-input');
    if (batchFileInput) {
        batchFileInput.addEventListener('change', handleBatchUpload);
    }
});

function handleSingleUpload(e) {
    if (e.target.files.length > 0) {
        processFiles([e.target.files[0]], false);
    }
}

function handleBatchUpload(e) {
    if (e.target.files.length > 0) {
        processFiles(Array.from(e.target.files), true);
    }
}

function processFiles(files, isBatch) {
    const processingDiv = document.getElementById('processing');
    const progressBar = document.getElementById('progress-bar');
    const fileCountSpan = document.getElementById('file-count');
    const chatMessages = document.getElementById('chat-messages');
    const batchResults = document.getElementById('batch-results');
    const resultsList = document.getElementById('results-list');

    // Reset UI
    fileCountSpan.textContent = files.length;
    progressBar.style.width = '0%';
    processingDiv.classList.remove('hidden');
    if (isBatch) {
        batchResults.classList.add('hidden');
        if (resultsList) resultsList.innerHTML = '';
    }

    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });

    const endpoint = isBatch ? '/batch_upload' : '/chat';
    
    fetch(endpoint, {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }

        if (isBatch) {
            displayBatchResults(data.results);
        } else {
            addMessageToChat(data);
        }
    })
    .catch(error => {
        alert('Error: ' + error.message);
    })
    .finally(() => {
        processingDiv.classList.add('hidden');
        if (fileInput) fileInput.value = '';
        if (batchFileInput) batchFileInput.value = '';
    });

    // Simulate progress (replace with actual progress events if supported by backend)
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 10;
        progressBar.style.width = `${Math.min(progress, 90)}%`;
        if (progress >= 100) {
            clearInterval(progressInterval);
        }
    }, 300);
}

function displayBatchResults(results) {
    const batchResults = document.getElementById('batch-results');
    const resultsList = document.getElementById('results-list');
    const chatMessages = document.getElementById('chat-messages');

    resultsList.innerHTML = '';
    
    results.forEach(result => {
        // Add to batch results list
        const resultItem = document.createElement('div');
        resultItem.className = `result-item ${result.status === 'success' ? 'result-success' : 'result-failed'}`;
        
        if (result.status === 'success') {
            resultItem.innerHTML = `
                <strong>${result.filename}</strong> (${result.original_language})
                <a href="/download/${result.translated_filename}" class="btn">Download</a>
            `;
            
            // Also add to chat messages
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message bot-message';
            messageDiv.innerHTML = `
                <strong>Translated from ${result.original_language}</strong><br>
                <a href="/download/${result.translated_filename}" class="btn">Download PDF</a>
            `;
            chatMessages.insertBefore(messageDiv, chatMessages.firstChild);
        } else {
            resultItem.innerHTML = `
                <strong>${result.filename}</strong> - Failed: ${result.error}
            `;
        }
        
        resultsList.appendChild(resultItem);
    });
    
    batchResults.classList.remove('hidden');
    document.getElementById('progress-bar').style.width = '100%';
}

function addMessageToChat(data) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.innerHTML = `
        <strong>Translated from ${data.original_language}</strong><br>
        <a href="/download/${data.translated_filename}" class="btn">Download PDF</a>
    `;
    chatMessages.insertBefore(messageDiv, chatMessages.firstChild);
    document.getElementById('progress-bar').style.width = '100%';
}
