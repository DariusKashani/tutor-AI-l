// Configuration
const API_BASE_URL = 'http://localhost:8742/api';
let activeTaskId = null;
let pollingIntervalId = null;
let consecutiveErrorCount = 0;  // Track consecutive errors
const MAX_CONSECUTIVE_ERRORS = 3;  // Max errors before stopping polling

// DOM Elements
const generatorForm = document.getElementById('generator-form');
const topicInput = document.getElementById('topic');
const sophisticationSlider = document.getElementById('sophistication');
const sophisticationValue = document.getElementById('sophistication-value');
const durationSlider = document.getElementById('duration');
const durationValue = document.getElementById('duration-value');
const useGmApiCheckbox = document.getElementById('use-gm-api');
const dryRunCheckbox = document.getElementById('dry-run');
const modelSelection = document.getElementById('model-selection');
const generateBtn = document.getElementById('generate-btn');
const resetBtn = document.getElementById('reset-btn');
const resultContainer = document.getElementById('result-container');
const resultMessage = document.getElementById('result-message');
const resultVideo = document.getElementById('result-video');
const newTutorialBtn = document.getElementById('new-tutorial-btn');
const downloadBtn = document.getElementById('download-btn');
const errorContainer = document.getElementById('error-container');
const errorMessage = document.getElementById('error-message');
const tryAgainBtn = document.getElementById('try-again-btn');
const loaderOverlay = document.getElementById('loader-overlay');
const loaderText = document.getElementById('loader-text');
const progressBar = document.getElementById('progress-bar');
const progressText = document.getElementById('progress-text');

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing create page');
    setupEventListeners();
    updateValueLabels();
    
    // Check if there was an active task from a previous session
    const savedTaskId = localStorage.getItem('activeTaskId');
    if (savedTaskId) {
        console.log(`Found saved task ID: ${savedTaskId}`);
        checkSavedTask(savedTaskId);
    }
});

// Check if there's a saved task and resume it
async function checkSavedTask(taskId) {
    try {
        console.log(`Checking status of saved task: ${taskId}`);
        const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
        
        if (response.ok) {
            const taskData = await response.json();
            
            if (taskData.status === 'processing' || taskData.status === 'running') {
                console.log('Resuming saved task that was in progress');
                // Task is still running, resume monitoring
                activeTaskId = taskId;
                showLoading('Resuming task...');
                generatorForm.classList.add('hidden');
                startPolling(taskId);
                return;
            } else if (taskData.status === 'completed') {
                console.log('Found completed task from previous session');
                // Task is complete, show the results
                handleTaskComplete(taskData);
                return;
            }
        }
        
        // If we got here, either the task wasn't found or it failed
        // Clear the saved task ID
        console.log('Saved task is no longer valid, clearing');
        localStorage.removeItem('activeTaskId');
        
    } catch (error) {
        console.error('Error checking saved task:', error);
        localStorage.removeItem('activeTaskId');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Update value labels when sliders change
    sophisticationSlider.addEventListener('input', updateValueLabels);
    durationSlider.addEventListener('input', updateValueLabels);
    
    // Toggle model selection based on GM API checkbox
    useGmApiCheckbox.addEventListener('change', () => {
        modelSelection.style.display = useGmApiCheckbox.checked ? 'block' : 'none';
    });
    
    // Form submission
    generateBtn.addEventListener('click', handleGenerateClick);
    
    // Reset form
    resetBtn.addEventListener('click', resetForm);
    
    // Result actions
    newTutorialBtn.addEventListener('click', () => {
        resultContainer.classList.add('hidden');
        generatorForm.classList.remove('hidden');
        resetForm();
    });
    
    downloadBtn.addEventListener('click', () => {
        const videoSrc = resultVideo.src;
        if (videoSrc) {
            const a = document.createElement('a');
            a.href = videoSrc;
            a.download = `math_tutorial_${Date.now()}.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }
    });
    
    // Error actions
    tryAgainBtn.addEventListener('click', () => {
        errorContainer.classList.add('hidden');
        generatorForm.classList.remove('hidden');
    });
}

// Update labels for sliders
function updateValueLabels() {
    // Update sophistication label
    const sophisticationValue = sophisticationSlider.value;
    let sophisticationText = 'Beginner';
    if (sophisticationValue == 2) sophisticationText = 'Intermediate';
    if (sophisticationValue == 3) sophisticationText = 'Advanced';
    document.getElementById('sophistication-value').textContent = sophisticationText;
    
    // Update duration label
    const durationValue = durationSlider.value;
    document.getElementById('duration-value').textContent = `${durationValue} minute${durationValue > 1 ? 's' : ''}`;
}

// Handle the generate button click
async function handleGenerateClick() {
    // Validate form
    if (!topicInput.value.trim()) {
        showError('Please enter a math topic');
        return;
    }
    
    // Show loading overlay
    showLoading('Starting tutorial generation...');
    
    // Get form data
    const formData = {
        topic: topicInput.value.trim(),
        level: getSophisticationLevel(),
        duration: parseInt(durationSlider.value),
        use_gm_api: useGmApiCheckbox.checked,
        dry_run: dryRunCheckbox.checked
    };
    
    // Add model parameter if GM API is enabled
    if (useGmApiCheckbox.checked) {
        formData.gm_model = getSelectedModel();
    }
    
    try {
        console.log('Submitting tutorial generation request:', formData);
        
        // Submit the tutorial generation request
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to start tutorial generation');
        }
        
        const data = await response.json();
        activeTaskId = data.task_id;
        
        // Save the task ID in case the page is refreshed
        localStorage.setItem('activeTaskId', activeTaskId);
        
        console.log(`Task created with ID: ${activeTaskId}`);
        
        // Start polling for task status
        startPolling(activeTaskId);
        
        // Hide the form while processing
        generatorForm.classList.add('hidden');
    } catch (error) {
        console.error('Error starting tutorial generation:', error);
        hideLoading();
        showError(`Failed to start tutorial generation: ${error.message}`);
    }
}

// Start polling for task status
function startPolling(taskId) {
    if (pollingIntervalId) {
        clearInterval(pollingIntervalId);
    }
    
    // Reset error counter
    consecutiveErrorCount = 0;
    
    // Update progress immediately
    updateTaskStatus(taskId);
    
    // Then poll every 2 seconds
    pollingIntervalId = setInterval(async () => {
        try {
            const completed = await updateTaskStatus(taskId);
            if (completed) {
                clearInterval(pollingIntervalId);
                pollingIntervalId = null;
                
                // Clear the saved task ID if completed successfully
                localStorage.removeItem('activeTaskId');
            }
            // Reset error count on successful request
            consecutiveErrorCount = 0;
        } catch (error) {
            console.error('Error polling for task status:', error);
            consecutiveErrorCount++;
            
            // Log the error count for debugging
            console.log(`Consecutive error count: ${consecutiveErrorCount}/${MAX_CONSECUTIVE_ERRORS}`);
            
            // If we've had too many consecutive errors, stop polling
            if (consecutiveErrorCount >= MAX_CONSECUTIVE_ERRORS) {
                clearInterval(pollingIntervalId);
                pollingIntervalId = null;
                hideLoading();
                
                // Handle different error types differently
                if (error.message.includes('Task not found')) {
                    showError(
                        'Task not found or was lost during server restart',
                        'The server may have restarted during processing. Please try again.'
                    );
                } else {
                    showError(
                        `Failed to get task status: ${error.message}`,
                        'There was a problem communicating with the server. Please try again later.'
                    );
                }
                
                // Clear the saved task ID since it's no longer valid
                localStorage.removeItem('activeTaskId');
            }
        }
    }, 2000);
}

// Update the task status
async function updateTaskStatus(taskId) {
    console.log(`Checking status for task: ${taskId}`);
    const response = await fetch(`${API_BASE_URL}/status/${taskId}`);
    
    if (!response.ok) {
        if (response.status === 404) {
            // Try to get more detailed error information
            const errorData = await response.json();
            const availableTasks = errorData.active_tasks || [];
            
            console.error(`Task not found. Available tasks: ${availableTasks.join(', ')}`);
            throw new Error(`Task not found. It may have been deleted or never existed. Available tasks: ${availableTasks.length}`);
        }
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const taskData = await response.json();
    console.log('Task status update:', taskData);
    
    // Update the progress
    updateProgress(
        taskData.progress || 0,
        taskData.message || 'Processing...'
    );
    
    // Check if task is completed
    if (taskData.status === 'completed') {
        handleTaskComplete(taskData);
        return true;
    }
    
    // Check if task failed
    if (taskData.status === 'error' || taskData.status === 'failed') {
        handleTaskError(taskData);
        return true;
    }
    
    // Task is still in progress
    return false;
}

// Handle completed task
function handleTaskComplete(taskData) {
    hideLoading();
    
    console.log('Task completed successfully:', taskData);
    
    // Get the video URL from the result
    let videoUrl = '';
    if (typeof taskData.result === 'string') {
        videoUrl = `${API_BASE_URL}/videos/${taskData.result.split('/').pop()}`;
    } else if (taskData.result && taskData.result.video_url) {
        videoUrl = `${API_BASE_URL}${taskData.result.video_url}`;
    }
    
    console.log(`Video URL: ${videoUrl}`);
    
    // Update the video player
    if (videoUrl) {
        resultVideo.src = videoUrl;
        resultVideo.load();
    }
    
    // Update the result message
    resultMessage.textContent = `Your math tutorial on "${topicInput.value}" has been successfully generated.`;
    
    // Show the result container
    resultContainer.classList.remove('hidden');
}

// Handle task error
function handleTaskError(taskData) {
    hideLoading();
    
    console.error('Task failed with error:', taskData.error);
    
    // Show error details
    let errorDetails = taskData.error || 'An unknown error occurred';
    
    // If error is a long string with stack traces, trim it
    if (errorDetails.length > 200) {
        errorDetails = errorDetails.substring(0, 200) + '...\n\n(See console for full error details)';
        console.error('Full error details:', taskData.error);
    }
    
    errorMessage.textContent = errorDetails;
    errorContainer.classList.remove('hidden');
    
    // Clear the saved task ID since it failed
    localStorage.removeItem('activeTaskId');
}

// Helper functions
function getSophisticationLevel() {
    const level = parseInt(sophisticationSlider.value);
    switch (level) {
        case 1: return 'beginner';
        case 2: return 'intermediate';
        case 3: return 'advanced';
        default: return 'beginner';
    }
}

function getSelectedModel() {
    const radioButtons = document.getElementsByName('model');
    for (let i = 0; i < radioButtons.length; i++) {
        if (radioButtons[i].checked) {
            return radioButtons[i].value;
        }
    }
    return 'gpt4o';  // Default
}

function resetForm() {
    topicInput.value = '';
    sophisticationSlider.value = 1;
    durationSlider.value = 3;
    useGmApiCheckbox.checked = true;
    dryRunCheckbox.checked = false;
    updateValueLabels();
    
    // Clear any active task
    activeTaskId = null;
    localStorage.removeItem('activeTaskId');
}

// UI helper functions
function showLoading(message = 'Loading...') {
    loaderText.textContent = message;
    progressBar.style.width = '0%';
    progressText.textContent = '0%';
    loaderOverlay.classList.remove('hidden');
}

function hideLoading() {
    loaderOverlay.classList.add('hidden');
}

function updateProgress(percent, message) {
    console.log(`Progress update: ${percent}% - ${message}`);
    progressBar.style.width = `${percent}%`;
    progressText.textContent = `${Math.round(percent)}%`;
    if (message) {
        loaderText.textContent = message;
    }
}

function showError(message, details = null) {
    console.error('Error:', message, details);
    errorMessage.innerHTML = message;
    
    if (details) {
        errorMessage.innerHTML += `<p class="error-details">${details}</p>`;
    }
    
    errorContainer.classList.remove('hidden');
    generatorForm.classList.add('hidden');
} 