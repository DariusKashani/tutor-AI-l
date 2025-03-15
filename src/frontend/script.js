// Configuration
const API_BASE_URL = 'http://localhost:8742/api';
const POLL_INTERVAL = 1000; // 1 second

// DOM elements
const topicInput = document.getElementById('topic');
const sophisticationSlider = document.getElementById('sophistication');
const sophisticationValue = document.getElementById('sophistication-value');
const durationSlider = document.getElementById('duration');
const durationValue = document.getElementById('duration-value');
const useGmApiCheckbox = document.getElementById('use-gm-api');
const dryRunCheckbox = document.getElementById('dry-run');
const modelSelection = document.getElementById('model-selection');
const generateBtn = document.getElementById('generate-btn');
const cancelBtn = document.getElementById('cancel-btn');
const newTutorialBtn = document.getElementById('new-tutorial-btn');
const tryAgainBtn = document.getElementById('try-again-btn');

const generatorForm = document.getElementById('generator-form');
const progressContainer = document.getElementById('progress-container');
const progressBar = document.getElementById('progress-bar');
const progressStatus = document.getElementById('progress-status');
const progressMessage = document.getElementById('progress-message');
const resultContainer = document.getElementById('result-container');
const resultMessage = document.getElementById('result-message');
const resultVideo = document.getElementById('result-video');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');

const videosContainer = document.getElementById('videos-container');
const noVideosMessage = document.getElementById('no-videos-message');
const loaderOverlay = document.getElementById('loader-overlay');
const loaderText = document.getElementById('loader-text');
const progressText = document.getElementById('progress-text');

// State
let currentTaskId = null;
let pollTimer = null;
let errorCounter = 0;

// Update UI based on slider values
sophisticationSlider.addEventListener('input', () => {
    const level = parseInt(sophisticationSlider.value);
    let levelText = 'Beginner';
    
    if (level === 2) levelText = 'Intermediate';
    else if (level === 3) levelText = 'Advanced';
    
    sophisticationValue.textContent = levelText;
});

durationSlider.addEventListener('input', () => {
    const duration = parseInt(durationSlider.value);
    durationValue.textContent = `${duration} minute${duration !== 1 ? 's' : ''}`;
});

// Toggle model selection visibility based on GM API checkbox
useGmApiCheckbox.addEventListener('change', () => {
    modelSelection.style.display = useGmApiCheckbox.checked ? 'block' : 'none';
});

// Generate button click handler
generateBtn.addEventListener('click', async () => {
    const topic = topicInput.value.trim();
    
    if (!topic) {
        alert('Please enter a math topic');
        topicInput.focus();
        return;
    }
    
    // Reset error counter
    errorCounter = 0;
    
    // Get all form values
    const level = getLevelText(parseInt(sophisticationSlider.value));
    const duration = parseInt(durationSlider.value);
    const useGmApi = useGmApiCheckbox.checked;
    const dryRun = dryRunCheckbox.checked;
    const gm_model = document.querySelector('input[name="model"]:checked').value;
    
    // Show progress UI
    showProgress();
    
    try {
        // Start task on the server
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                topic,
                level,
                duration,
                use_gm_api: useGmApi, 
                gm_model,
                dry_run: dryRun
            }),
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentTaskId = data.task_id;
            console.log('Task created:', currentTaskId);
            // Start polling for progress
            startPolling(currentTaskId);
        } else {
            showError(data.error || 'Failed to start generation task', data);
        }
    } catch (error) {
        showError(`Error: ${error.message}`, error);
    }
});

// Cancel button click handler
cancelBtn.addEventListener('click', () => {
    if (currentTaskId) {
        stopPolling();
        resetUI();
    }
});

// New tutorial button click handler
newTutorialBtn.addEventListener('click', resetUI);

// Try again button click handler
tryAgainBtn.addEventListener('click', resetUI);

// Helper Functions

function getLevelText(level) {
    switch (level) {
        case 1: return 'beginner';
        case 2: return 'intermediate';
        case 3: return 'advanced';
        default: return 'beginner';
    }
}

function showProgress() {
    generatorForm.classList.add('d-none');
    progressContainer.classList.remove('d-none');
    resultContainer.classList.add('d-none');
    errorContainer.classList.add('d-none');
    
    // Reset progress
    updateProgress(0, 'Starting tutorial generation...');
}

function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressBar.setAttribute('aria-valuenow', percent);
    progressBar.textContent = `${percent}%`;
    
    if (message) {
        progressMessage.textContent = message;
    }
    
    // Update status text based on progress
    if (percent < 20) {
        progressStatus.textContent = 'Generating Script...';
    } else if (percent < 50) {
        progressStatus.textContent = 'Creating Animations...';
    } else if (percent < 75) {
        progressStatus.textContent = 'Rendering Scenes...';
    } else if (percent < 95) {
        progressStatus.textContent = 'Finalizing Video...';
    } else {
        progressStatus.textContent = 'Almost Done!';
    }
}

function showResult(result) {
    progressContainer.classList.add('d-none');
    resultContainer.classList.remove('d-none');
    
    // Extract filename from the result path
    const filename = result.split('/').pop();
    resultMessage.textContent = `Your math tutorial on "${topicInput.value}" has been created.`;
    
    // Set video source
    resultVideo.src = `${API_BASE_URL}/videos/${filename}`;
    resultVideo.load();
}

function showError(message, details = null) {
    progressContainer.classList.add('d-none');
    errorContainer.classList.remove('d-none');
    
    let errorText = message;
    if (details) {
        errorText += `<br><br><strong>Technical Details:</strong><br><pre class="text-danger small">${JSON.stringify(details, null, 2)}</pre>`;
    }
    
    errorMessage.innerHTML = errorText;
    console.error('Error:', message, details);
}

function resetUI() {
    if (pollTimer) {
        stopPolling();
    }
    
    currentTaskId = null;
    
    generatorForm.classList.remove('d-none');
    progressContainer.classList.add('d-none');
    resultContainer.classList.add('d-none');
    errorContainer.classList.add('d-none');
    
    // Reset video 
    resultVideo.src = '';
}

function startPolling(taskId) {
    // Clear any existing timer
    stopPolling();
    
    // Set up polling
    pollTimer = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
            const data = await response.json();
            
            if (response.ok) {
                // Update progress
                updateProgress(data.progress, data.message);
                
                // Check if task is complete
                if (data.status === 'completed') {
                    stopPolling();
                    showResult(data.result);
                } 
                // Check if task failed
                else if (data.status === 'failed') {
                    stopPolling();
                    showError(data.error || 'Tutorial generation failed', data);
                }
            } else {
                // If task not found or other error
                stopPolling();
                showError(data.error || 'Error checking task status', data);
                console.error('API Error:', response.status, data);
            }
        } catch (error) {
            console.error('Error polling task status:', error);
            // After 3 consecutive errors, show an error message
            errorCounter++;
            if (errorCounter > 3) {
                stopPolling();
                showError(`Error communicating with the server: ${error.message}`, error);
            }
        }
    }, POLL_INTERVAL);
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

// Initial UI setup
modelSelection.style.display = useGmApiCheckbox.checked ? 'block' : 'none';

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing homepage');
    setupEventListeners();
    
    // Fetch videos on page load
    fetchVideos();
});

// Setup event listeners
function setupEventListeners() {
    // Add a reload button to refresh the video list
    const reloadButton = document.createElement('button');
    reloadButton.className = 'reload-btn';
    reloadButton.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh';
    reloadButton.addEventListener('click', () => {
        console.log('Manually refreshing video list');
        fetchVideos();
    });
    
    // Add the button to the section header
    const sectionHeader = document.querySelector('.video-grid-section .section-header');
    if (sectionHeader) {
        sectionHeader.appendChild(reloadButton);
    }
}

// Fetch videos from the API
async function fetchVideos() {
    console.log('Fetching videos from API');
    showLoading('Loading videos...');
    
    try {
        // Get all tasks from the API
        const response = await fetch(`${API_BASE_URL}/tasks`);
        
        if (!response.ok) {
            throw new Error('Failed to fetch videos');
        }
        
        const data = await response.json();
        console.log('Fetched tasks:', data);
        
        // Display the tasks as videos
        displayVideos(data.tasks || []);
        
        hideLoading();
    } catch (error) {
        console.error('Error fetching videos:', error);
        hideLoading();
        
        // Show error message
        noVideosMessage.innerHTML = `
            <p>Error loading videos: ${error.message}</p>
            <button class="btn primary-btn" onclick="fetchVideos()">Try Again</button>
        `;
        noVideosMessage.style.display = 'block';
    }
}

// Display videos in the grid
function displayVideos(tasks) {
    console.log(`Displaying ${tasks.length} tasks`);
    
    // Filter tasks to only show completed ones with results
    const completedTasks = tasks.filter(task => 
        task.status === 'completed' && task.result
    );
    
    // Clear the container first (except for the create new card)
    const createNewCard = document.querySelector('.video-card.create-new');
    videosContainer.innerHTML = '';
    
    if (createNewCard) {
        videosContainer.appendChild(createNewCard);
    }
    
    // Check if there are videos to display
    if (completedTasks.length === 0) {
        console.log('No completed videos found');
        noVideosMessage.style.display = 'block';
        return;
    }
    
    // Hide the no videos message
    noVideosMessage.style.display = 'none';
    
    // Add each video to the grid
    completedTasks.forEach(task => {
        const videoCard = createVideoCard(task);
        videosContainer.appendChild(videoCard);
    });
    
    console.log(`Displayed ${completedTasks.length} videos`);
}

// Create a video card element
function createVideoCard(video) {
    console.log('Creating video card for:', video);
    
    // Get the video URL
    let videoUrl = '';
    if (typeof video.result === 'string') {
        videoUrl = `${API_BASE_URL}/videos/${video.result.split('/').pop()}`;
    } else if (video.result && video.result.video_url) {
        videoUrl = `${API_BASE_URL}${video.result.video_url}`;
    }
    
    // Get the topic from parameters or use a default
    const topic = video.params && video.params.topic ? video.params.topic : 'Math Tutorial';
    
    // Create the video card element
    const card = document.createElement('div');
    card.className = 'video-card';
    card.innerHTML = `
        <div class="thumbnail">
            <img src="https://via.placeholder.com/320x180.png?text=Math+Tutorial" alt="${topic}">
            <div class="play-icon">
                <i class="fas fa-play"></i>
            </div>
        </div>
        <div class="video-info">
            <h3>${topic}</h3>
            <p>${getLevelText(video.params?.level || 'beginner')}</p>
        </div>
        <div class="video-meta">
            <span><i class="fas fa-clock"></i> ${video.params?.duration || 3} min</span>
            <span><i class="fas fa-calendar"></i> ${new Date(video.update_time * 1000).toLocaleDateString()}</span>
        </div>
    `;
    
    // Add click event to view the video
    card.addEventListener('click', () => {
        window.location.href = `view.html?id=${video.task_id}&url=${encodeURIComponent(videoUrl)}`;
    });
    
    return card;
}

// UI helper functions
function showLoading(message = 'Loading...') {
    loaderText.textContent = message;
    loaderOverlay.classList.remove('hidden');
}

function hideLoading() {
    loaderOverlay.classList.add('hidden');
}

function updateProgress(percent, message) {
    progressBar.style.width = `${percent}%`;
    progressText.textContent = `${Math.round(percent)}%`;
    if (message) {
        loaderText.textContent = message;
    }
}

function showError(message) {
    // You can implement a toast or notification system here
    console.error(message);
    // For now, just alert
    alert(message);
} 