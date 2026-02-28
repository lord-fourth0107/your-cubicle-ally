// Screen elements
const welcomeScreen = document.getElementById('welcome-screen');
const jobDescriptionScreen = document.getElementById('job-description-screen');
const trainingsScreen = document.getElementById('trainings-screen');

// Buttons & inputs
const startOnboardingBtn = document.getElementById('start-onboarding-btn');
const jobDescriptionInput = document.getElementById('job-description-input');
const submitJobBtn = document.getElementById('submit-job-btn');
const trainingsList = document.getElementById('trainings-list');

// Default onboarding trainings (can be customized later by backend based on job description)
const DEFAULT_TRAININGS = [
  {
    id: 1,
    title: 'Company Culture & Values',
    description: 'Learn about our mission, values, and what makes us unique',
  },
  {
    id: 2,
    title: 'Security & Compliance Basics',
    description: 'Essential security practices and compliance requirements',
  },
  {
    id: 3,
    title: 'Tools & Systems Overview',
    description: 'Get familiar with the tools you\'ll use every day',
  },
  {
    id: 4,
    title: 'Team Structure & Key Contacts',
    description: 'Who\'s who and how to find the right people',
  },
  {
    id: 5,
    title: 'Development Workflow',
    description: 'Code review, deployment, and release processes',
  },
  {
    id: 6,
    title: 'Career Growth & Learning',
    description: 'Resources for your professional development',
  },
];

function showScreen(screen) {
  welcomeScreen.classList.remove('active');
  jobDescriptionScreen.classList.remove('active');
  trainingsScreen.classList.remove('active');

  screen.classList.add('active');
}

function renderTrainingsList() {
  trainingsList.innerHTML = '';
  const trainings = DEFAULT_TRAININGS;

  trainings.forEach((training) => {
    const li = document.createElement('li');
    li.className = 'training-item';
    li.dataset.id = training.id;
    li.innerHTML = `
      <span class="training-number">${String(training.id).padStart(2, '0')}</span>
      <div class="training-content">
        <div class="training-title">${training.title}</div>
        <div class="training-desc">${training.description}</div>
      </div>
      <span class="training-arrow">→</span>
    `;

    li.addEventListener('click', () => {
      handleTrainingClick(training);
    });

    trainingsList.appendChild(li);
  });
}

function handleTrainingClick(training) {
  // Placeholder - you can open a training detail view, external link, or modal
  console.log('Training clicked:', training);
  alert(`Opening: ${training.title}\n\n(Connect to your backend to load actual training content)`);
}

// Back buttons
const backToWelcomeBtn = document.getElementById('back-to-welcome-btn');
const backToJobBtn = document.getElementById('back-to-job-btn');

// Event listeners
startOnboardingBtn.addEventListener('click', () => {
  showScreen(jobDescriptionScreen);
});

backToWelcomeBtn.addEventListener('click', () => {
  showScreen(welcomeScreen);
});

backToJobBtn.addEventListener('click', () => {
  showScreen(jobDescriptionScreen);
});

submitJobBtn.addEventListener('click', () => {
  const jobDescription = jobDescriptionInput.value.trim();
  if (!jobDescription) {
    jobDescriptionInput.focus();
    jobDescriptionInput.style.borderColor = '#ef4444';
    setTimeout(() => {
      jobDescriptionInput.style.borderColor = '';
    }, 2000);
    return;
  }

  // Store job description for later use (e.g., send to backend)
  window.jobDescription = jobDescription;

  // TODO: In production, call your backend API here to get personalized trainings
  // based on job description. For now we use the default list.
  renderTrainingsList();
  showScreen(trainingsScreen);
});

// Initialize
renderTrainingsList();
