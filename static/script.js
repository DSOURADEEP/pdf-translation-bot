document.addEventListener('DOMContentLoaded', function () {
    const fileInput = document.getElementById('file-input');
    const chatMessages = document.getElementById('chat-messages');
    const processingDiv = document.getElementById('processing');

    if (fileInput) {
        fileInput.addEventListener('change', async function () {
            if (this.files.length > 0) {
                const fileLabel = document.querySelector('label[for="file-input"]');
                fileLabel.textContent = this.files[0].name;

                processingDiv.classList.remove('hidden');

                try {
                    const formData = new FormData();
                    formData.append('file', this.files[0]);

                    const response = await fetch('/chat', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();

                    if (response.ok) {
                        const messageDiv = document.createElement('div');
                        messageDiv.className = 'message bot-message';
                        messageDiv.innerHTML = `
                            <strong>Translated from ${data.original_language}</strong><br>
                            <a href="/download/${data.translated_filename}" class="btn">Download PDF</a>
                        `;
                        chatMessages.insertBefore(messageDiv, chatMessages.firstChild);
                    } else {
                        alert(data.error || 'Error processing file');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    processingDiv.classList.add('hidden');
                    document.querySelector('label[for="file-input"]').textContent = 'Choose PDF File';
                    this.value = '';
                }
            }
        });
    }
});
