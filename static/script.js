// --- Tab functionality 
function toggleTab(tabName) {
    const tabContents = document.querySelectorAll('.tab-content');
    tabContents.forEach(tab => tab.classList.remove('active'));
    const selectedTab = document.getElementById(`${tabName}-content`);
    if (selectedTab) selectedTab.classList.add('active');
}

// Helper: get token
function getToken() {
    return localStorage.getItem('access_token');
}

// Helper: set token & user info
function setUser(token, user) {
    if (token) localStorage.setItem('access_token', token);
    if (user) localStorage.setItem('user', JSON.stringify(user));
}

// On DOM loaded
document.addEventListener('DOMContentLoaded', function() {
    const generateBtn = document.getElementById('generate-btn');
    if (generateBtn) generateBtn.addEventListener('click', generateFlashcards);

    // Flashcard flip
    document.addEventListener('click', function(e) {
        const flashcard = e.target.closest('.flashcard');
        if (flashcard) flashcard.classList.toggle('flipped');
    });

    // Signup
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(signupForm);
            const userData = {
                name: formData.get('name'),
                email: formData.get('email'),
                password: formData.get('password')
            };
            try {
                const res = await fetch('/api/signup', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(userData)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Signup failed');
                alert('Account created! You are logged in.');
                setUser(data.access_token, {id: data.user_id});
                signupForm.reset();
            } catch (err) {
                alert('Error creating account: ' + err.message);
            }
        });
    }

    // Login
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(loginForm);
            const userData = {
                email: formData.get('email'),
                password: formData.get('password')
            };
            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(userData)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || 'Login failed');
                setUser(data.access_token, data.user);
                alert('Login successful. Welcome back, ' + data.user.name);
                loginForm.reset();
            } catch (err) {
                alert('Login error: ' + err.message);
            }
        });
    }

    // Upgrade button (on both index & generate pages)
    const upgradeBtns = document.querySelectorAll('#upgrade-pro-btn, #upgrade-btn');
    upgradeBtns.forEach(btn => {
        if (!btn) return;
        btn.addEventListener('click', async function() {
            // ensure user logged in
            const token = getToken();
            if (!token) {
                if (!confirm('You need to be logged in to buy Pro. Log in now?')) return;
                toggleTab('login');
                return;
            }
            // Example: single purchase / subscription creation parameters
            // Adjust amount and metadata as needed. Use sandbox keys first.
            const payload = {
                amount: 2000,       // check IntaSend docs for units; use sandbox to verify
                currency: 'KES',
                title: 'Flipwise Pro - 1 month',
                description: 'Monthly subscription to Flipwise Pro'
            };
            try {
                const res = await fetch('/api/create-paymentlink', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer ' + token
                    },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || JSON.stringify(data));
                // IntaSend will return a URL in the response body (depends on API)
                // We'll try to find it in common keys; inspect "intasend_response" structure if different
                const resp = data.intasend_response || data;
                // Try typical keys used by payment-link APIs
                let checkoutUrl = resp.get ? resp.get('url') : null;
                // If response is object with data or invoice data:
                if (!checkoutUrl) {
                    if (resp.data && resp.data.url) checkoutUrl = resp.data.url;
                    else if (resp.url) checkoutUrl = resp.url;
                    else if (resp.checkout_url) checkoutUrl = resp.checkout_url;
                    else if (resp.payment_url) checkoutUrl = resp.payment_url;
                }
                if (!checkoutUrl) {
                    // fallback: stringify the response so developer can inspect
                    alert('Payment link created. Inspect console for response.');
                    console.log('IntaSend response:', resp);
                    return;
                }
                // redirect user to the IntaSend checkout page
                window.location.href = checkoutUrl;
            } catch (err) {
                alert('Failed to create payment link: ' + err.message);
            }
        });
    });
});

// --- Flashcards generation and save (mostly unchanged) ---
async function generateFlashcards() {
    const studyNotes = document.getElementById('study-notes').value;
    if (!studyNotes || !studyNotes.trim()) { alert('Please enter some study notes first!'); return; }

    const generateBtn = document.getElementById('generate-btn');
    const originalText = generateBtn.textContent;
    generateBtn.textContent = 'Generating...'; generateBtn.disabled = true;

    const container = document.getElementById('flashcards-container');
    container.innerHTML = '<div class="loading">Generating your flashcards...</div>';

    try {
        const response = await fetch('/api/generate-flashcards', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ text: studyNotes })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Failed to generate flashcards');
        displayFlashcards(data.flashcards);
        // Save if logged in
        await saveFlashcards(data.flashcards);
    } catch (error) {
        console.error('Error:', error);
        alert('Error generating flashcards: ' + error.message);
        // fallback
        const sampleQuestions = [
            { question: "What is the capital of France?", answer: "Paris is the capital and most populous city of France." },
            { question: "What is 2 + 2?", answer: "4" }
        ];
        displayFlashcards(sampleQuestions);
    } finally {
        generateBtn.textContent = originalText; generateBtn.disabled = false;
    }
}

function displayFlashcards(flashcards) {
    const flashcardsContainer = document.getElementById('flashcards-container');
    flashcardsContainer.innerHTML = '';
    flashcards.forEach((card, index) => {
        const flashcard = document.createElement('div');
        flashcard.className = 'flashcard';
        flashcard.innerHTML = `
            <div class="flashcard-inner">
                <div class="flashcard-front">
                    <h3>Question ${index + 1}</h3>
                    <p>${card.question}</p>
                    <p class="flip-instruction">(Click to flip)</p>
                </div>
                <div class="flashcard-back">
                    <h3>Answer</h3>
                    <p>${card.answer}</p>
                    <p class="flip-instruction">(Click to flip back)</p>
                </div>
            </div>
        `;
        flashcardsContainer.appendChild(flashcard);
    });
}

async function saveFlashcards(flashcards) {
    const token = getToken();
    if (!token) {
        console.log('Not logged in — flashcards not saved automatically.');
        return;
    }
    try {
        const response = await fetch('/api/save-flashcards', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({ flashcards })
        });
        const data = await response.json();
        if (!response.ok) {
            console.error('Failed to save flashcards:', data.error || data);
        } else {
            console.log('Flashcards saved successfully:', data.message);
        }
    } catch (error) {
        console.error('Error saving flashcards:', error);
    }
}