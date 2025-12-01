// Gestion de la navigation mobile
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.getElementById('navMenu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Fermer les messages flash après 5 secondes
    setTimeout(() => {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(msg => msg.remove());
    }, 5000);

    // Initialiser l'application selon la page
    const currentPage = window.location.pathname;
    
    if (currentPage === '/' || currentPage === '/index.html') {
        initHomePage();
    } else if (currentPage === '/login') {
        initLoginPage();
    } else if (currentPage === '/register') {
        initRegisterPage();
    } else if (currentPage === '/dashboard') {
        initDashboardPage();
    } else if (currentPage.startsWith('/bourse/')) {
        initBourseDetailPage();
    } else if (currentPage === '/admin') {
        initAdminPage();
    }
});

// Page d'accueil
function initHomePage() {
    const splashScreen = document.querySelector('.splash-screen');
    const mainContent = document.getElementById('accueil');
    
    // Navigation depuis la page de démarrage
    document.querySelectorAll('.btn-primary[href="#accueil"]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            splashScreen.style.display = 'none';
            mainContent.style.display = 'block';
            window.scrollTo(0, 0);
        });
    });

    // Charger les bourses populaires
    loadBourses('#boursesGrid');
}

// Page de connexion
function initLoginPage() {
    const loginForm = document.getElementById('loginForm');
    const loginBtn = document.getElementById('loginBtn');
    const loginText = document.getElementById('loginText');
    const loginLoading = document.getElementById('loginLoading');

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            numero_whatsapp: document.getElementById('numero_whatsapp').value,
            password: document.getElementById('password').value
        };

        // Afficher le loading
        loginText.style.display = 'none';
        loginLoading.style.display = 'inline-block';
        loginBtn.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:5000/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                showFlashMessage(result.message, 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1000);
            } else {
                showFlashMessage(result.message, 'error');
            }
        } catch (error) {
            showFlashMessage('Erreur de connexion', 'error');
        } finally {
            loginText.style.display = 'inline-block';
            loginLoading.style.display = 'none';
            loginBtn.disabled = false;
        }
    });
}

// Page d'inscription
function initRegisterPage() {
    const registerForm = document.getElementById('registerForm');
    const registerBtn = document.getElementById('registerBtn');
    const registerText = document.getElementById('registerText');
    const registerLoading = document.getElementById('registerLoading');

    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = {
            nom: document.getElementById('nom').value,
            prenom: document.getElementById('prenom').value,
            numero_whatsapp: document.getElementById('numero_whatsapp').value,
            email: document.getElementById('email').value,
            password: document.getElementById('password').value,
            confirm_password: document.getElementById('confirm_password').value
        };

        // Validation des mots de passe
        if (formData.password !== formData.confirm_password) {
            showFlashMessage('Les mots de passe ne correspondent pas', 'error');
            return;
        }

        // Afficher le loading
        registerText.style.display = 'none';
        registerLoading.style.display = 'inline-block';
        registerBtn.disabled = true;

        try {
            const response = await fetch('http://127.0.0.1:5000/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                showFlashMessage(result.message, 'success');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            } else {
                showFlashMessage(result.message, 'error');
            }
        } catch (error) {
            showFlashMessage('Erreur d\'inscription', 'error');
        } finally {
            registerText.style.display = 'inline-block';
            registerLoading.style.display = 'none';
            registerBtn.disabled = false;
        }
    });
}

// Tableau de bord
function initDashboardPage() {
    // Mettre à jour le nom de l'utilisateur
    const userData = getUserData();
    if (userData) {
        document.getElementById('userName').textContent = userData.prenom + ' ' + userData.nom;
        document.getElementById('userWelcome').textContent = 'Bonjour, ' + userData.prenom;
    }

    // Charger les statistiques
    loadStats();
    
    // Charger les bourses recommandées
    loadBourses('#boursesGrid');

    // Gestion de la déconnexion

    // Gestion de la déconnexion
    document.getElementById('logoutBtn').addEventListener('click', async function(e) {
        e.preventDefault();
        
        try {
            const response = await fetch('http://127.0.0.1:5000/api/logout');
            const result = await response.json();
            
            if (result.success) {
                showFlashMessage(result.message, 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            }
        } catch (error) {
            console.error('Erreur de déconnexion:', error);
        }
    });

    
}

// Détail d'une bourse
function initBourseDetailPage() {
    const bourseId = window.location.pathname.split('/').pop();
    
    // Mettre à jour le nom de l'utilisateur
    const userData = getUserData();
    if (userData) {
        document.getElementById('userWelcome').textContent = 'Bonjour, ' + userData.prenom;
    }

    // Charger les détails de la bourse
    loadBourseDetail(bourseId);

    // Gestion de la déconnexion
    document.getElementById('logoutBtn').addEventListener('click', async function(e) {
        e.preventDefault();
        
        try {
            const response = await fetch('http://127.0.0.1:5000/api/logout');
            const result = await response.json();
            
            if (result.success) {
                showFlashMessage(result.message, 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            }
        } catch (error) {
            console.error('Erreur de déconnexion:', error);
        }
    });
}

// Panel d'administration
// Gestion de l'ajout de bourse avec médias
function initAdminPage() {
    // Charger les statistiques admin
    loadAdminStats();
    
    // Charger les bourses pour l'admin
    loadBourses('#adminBoursesGrid', true);

    // Gestion du formulaire d'ajout de bourse
    document.getElementById('addBourseForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const submitBtn = document.getElementById('submitBourseBtn');
        const submitText = document.getElementById('submitBourseText');
        const submitLoading = document.getElementById('submitBourseLoading');
        
        // Afficher le loading
        submitText.style.display = 'none';
        submitLoading.style.display = 'inline-block';
        submitBtn.disabled = true;
        
        try {
            const formData = new FormData(this);
            
            const response = await fetch('/api/bourses', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.success) {
                showFlashMessage(result.message, 'success');
                closeModal('addBourseModal');
                // Réinitialiser le formulaire
                this.reset();
                clearPreviews();
                // Recharger la liste des bourses
                loadBourses('#adminBoursesGrid', true);
            } else {
                showFlashMessage(result.message, 'error');
            }
        } catch (error) {
            console.error('Erreur:', error);
            showFlashMessage('Erreur lors de l\'ajout de la bourse', 'error');
        } finally {
            submitText.style.display = 'inline-block';
            submitLoading.style.display = 'none';
            submitBtn.disabled = false;
        }
    });

    // Gestion des prévisualisations d'images
    initFilePreviews();
}

function initFilePreviews() {
    // Prévisualisation image principale
    document.getElementById('imageInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        const preview = document.getElementById('imagePreview');
        preview.innerHTML = '';
        
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.style.maxWidth = '200px';
                img.style.maxHeight = '150px';
                img.style.borderRadius = '8px';
                preview.appendChild(img);
            }
            reader.readAsDataURL(file);
        }
    });

    // Prévisualisation vidéo
    document.getElementById('videoInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        const preview = document.getElementById('videoPreview');
        preview.innerHTML = '';
        
        if (file) {
            const video = document.createElement('video');
            video.src = URL.createObjectURL(file);
            video.controls = true;
            video.style.maxWidth = '200px';
            video.style.maxHeight = '150px';
            video.style.borderRadius = '8px';
            preview.appendChild(video);
        }
    });

    // Prévisualisation médias procédure
    document.getElementById('procedureMediasInput').addEventListener('change', function(e) {
        const files = e.target.files;
        const preview = document.getElementById('procedureMediasPreview');
        
        for (let file of files) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const container = document.createElement('div');
                container.style.position = 'relative';
                container.style.display = 'inline-block';
                
                if (file.type.startsWith('image/')) {
                    const img = document.createElement('img');
                    img.src = e.target.result;
                    img.style.width = '100px';
                    img.style.height = '80px';
                    img.style.objectFit = 'cover';
                    img.style.borderRadius = '4px';
                    container.appendChild(img);
                } else if (file.type.startsWith('video/')) {
                    const video = document.createElement('video');
                    video.src = e.target.result;
                    video.style.width = '100px';
                    video.style.height = '80px';
                    video.style.objectFit = 'cover';
                    video.style.borderRadius = '4px';
                    container.appendChild(video);
                }
                
                // Bouton de suppression
                const removeBtn = document.createElement('button');
                removeBtn.innerHTML = '×';
                removeBtn.style.position = 'absolute';
                removeBtn.style.top = '-5px';
                removeBtn.style.right = '-5px';
                removeBtn.style.background = 'red';
                removeBtn.style.color = 'white';
                removeBtn.style.border = 'none';
                removeBtn.style.borderRadius = '50%';
                removeBtn.style.width = '20px';
                removeBtn.style.height = '20px';
                removeBtn.style.cursor = 'pointer';
                removeBtn.onclick = function() {
                    container.remove();
                };
                container.appendChild(removeBtn);
                
                preview.appendChild(container);
            }
            reader.readAsDataURL(file);
        }
    });
}

function clearPreviews() {
    document.getElementById('imagePreview').innerHTML = '';
    document.getElementById('videoPreview').innerHTML = '';
    document.getElementById('procedureMediasPreview').innerHTML = '';
}

// Fonctions pour l'admin
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    clearPreviews();
}

// Fonctions utilitaires
function showFlashMessage(message, type) {
    const flashContainer = document.querySelector('.flash-messages') || createFlashContainer();
    const flashMessage = document.createElement('div');
    flashMessage.className = `flash-message flash-${type}`;
    flashMessage.textContent = message;
    flashContainer.appendChild(flashMessage);
    
    setTimeout(() => {
        flashMessage.remove();
    }, 5000);
}

function createFlashContainer() {
    const container = document.createElement('div');
    container.className = 'flash-messages';
    document.body.appendChild(container);
    return container;
}

function getUserData() {
    // Récupérer les données utilisateur depuis le localStorage ou une session
    try {
        return JSON.parse(localStorage.getItem('userData'));
    } catch (error) {
        return null;
    }
}

async function loadBourses(containerSelector, isAdmin = false) {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/bourses');
        const bourses = await response.json();

        const container = document.querySelector(containerSelector);
        if (!container) return;

        container.innerHTML = '';

        bourses.forEach(bourse => {
            const bourseCard = createBourseCard(bourse, isAdmin);
            container.appendChild(bourseCard);
        });
    } catch (error) {
        console.error('Erreur lors du chargement des bourses:', error);
        showFlashMessage('Erreur lors du chargement des bourses', 'error');
    }
}

function createBourseCard(bourse, isAdmin = false) {
    const card = document.createElement('div');
    card.className = 'bourse-card';
    card.innerHTML = `
        <div class="bourse-image">
            <svg viewBox="0 0 48 48" fill="currentColor" width="60" height="60">
                <path d="M24 4L6 14v20l18 10 18-10V14L24 4zm0 6l12 6.87v14.26L24 38 12 31.13V16.87L24 10z"/>
                <path d="M20 22l8 4.62V34l-8-4.62V22z"/>
            </svg>
        </div>
        <div class="bourse-content">
            <h3 class="bourse-title">${bourse.titre}</h3>
            <div class="bourse-university">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z"/>
                </svg>
                ${bourse.universite}, ${bourse.pays}
            </div>
            <p class="bourse-description">${bourse.description}</p>
            <div class="bourse-details">
                <div class="bourse-detail">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82zM12 3L1 9l11 6 9-4.91V17h2V9L12 3z"/>
                    </svg>
                    <span>${bourse.niveau_etude}</span>
                </div>
                <div class="bourse-detail">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1.41 16.09V20h-2.67v-1.93c-1.71-.36-3.16-1.46-3.27-3.4h1.96c.1 1.05.82 1.87 2.65 1.87 1.96 0 2.4-.98 2.4-1.59 0-.83-.44-1.61-2.67-2.14-2.48-.6-4.18-1.62-4.18-3.67 0-1.72 1.39-2.84 3.11-3.21V4h2.67v1.95c1.86.45 2.79 1.86 2.85 3.39H14.3c-.05-1.11-.64-1.87-2.22-1.87-1.5 0-2.4.68-2.4 1.64 0 .84.65 1.39 2.67 1.91 2.56.62 4.18 1.54 4.18 3.67 0 1.9-1.51 3-3.23 3.31z"/>
                    </svg>
                    <span>${bourse.montant_bourse}</span>
                </div>
            </div>
            <div class="bourse-actions">
                <a href="/bourse/${bourse.id}" class="btn-small btn-outline">Voir détails</a>
                ${isAdmin ? `
                    <button class="btn-small btn-outline" onclick="editBourse(${bourse.id})">Modifier</button>
                    <button class="btn-small btn-filled" onclick="deleteBourse(${bourse.id})">Supprimer</button>
                ` : '<button class="btn-small btn-filled">Postuler</button>'}
            </div>
        </div>
    `;
    return card;
}

async function loadBourseDetail(bourseId) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/api/bourse/${bourseId}`);
        const bourse = await response.json();

        if (bourse.error) {
            showFlashMessage(bourse.error, 'error');
            return;
        }

        // Mettre à jour les éléments de la page
        document.getElementById('bourseTitle').textContent = bourse.titre;
        document.getElementById('bourseUniversity').textContent = `${bourse.universite}, ${bourse.pays}`;
        document.getElementById('bourseDescription').textContent = bourse.description;
        document.getElementById('bourseNiveau').textContent = bourse.niveau_etude;
        document.getElementById('bourseMontant').textContent = bourse.montant_bourse;
        document.getElementById('bourseDateLimite').textContent = bourse.date_limite;
        document.getElementById('boursePays').textContent = bourse.pays;
        document.getElementById('bourseConditions').innerHTML = bourse.conditions.replace(/\n/g, '<br>');
        document.getElementById('bourseProcedure').innerHTML = bourse.procedure_postulation.replace(/\n/g, '<br>');

        // Mettre à jour le titre de la page
        document.title = `${bourse.titre} - ZoneBourse`;

    } catch (error) {
        console.error('Erreur lors du chargement des détails:', error);
        showFlashMessage('Erreur lors du chargement des détails', 'error');
    }
}

function loadStats() {
    // Simuler des statistiques (à remplacer par des appels API réels)
    document.getElementById('statsBourses').textContent = '12';
    document.getElementById('statsCandidatures').textContent = '5';
    document.getElementById('statsFavoris').textContent = '8';
    document.getElementById('statsAlertes').textContent = '3';
}

function loadAdminStats() {
    // Simuler des statistiques admin
    document.getElementById('statsUsers').textContent = '156';
    document.getElementById('statsBourses').textContent = '47';
    document.getElementById('statsUniversites').textContent = '32';
    document.getElementById('statsPays').textContent = '18';
}

// Fonctions pour l'admin
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'flex';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function editBourse(bourseId) {
    showFlashMessage('Fonctionnalité de modification à implémenter', 'success');
}

function deleteBourse(bourseId) {
    if (confirm('Êtes-vous sûr de vouloir supprimer cette bourse ?')) {
        showFlashMessage('Bourse supprimée avec succès', 'success');
        // Recharger la liste des bourses
        loadBourses('#adminBoursesGrid', true);
    }
}

// Gestion de la recherche
document.addEventListener('DOMContentLoaded', function() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const bourseCards = document.querySelectorAll('.bourse-card');
            
            bourseCards.forEach(card => {
                const title = card.querySelector('.bourse-title').textContent.toLowerCase();
                const university = card.querySelector('.bourse-university').textContent.toLowerCase();
                const description = card.querySelector('.bourse-description').textContent.toLowerCase();
                
                if (title.includes(searchTerm) || university.includes(searchTerm) || description.includes(searchTerm)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });
});