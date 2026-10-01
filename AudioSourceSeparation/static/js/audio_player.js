function formatTime(sec) {
    if (!isFinite(sec) || isNaN(sec)) return "0:00";
    sec = Math.floor(sec);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return m + ":" + (s < 10 ? "0" : "") + s;
}

function updateProgress(id) {
    const audio = document.getElementById(id);
    if (!audio) return;
    
    const fill = document.getElementById('fill-' + id);
    const timeDisplay = document.getElementById('time-' + id);
    if (!fill || !timeDisplay) return;

    // Debug: Log if duration is missing
    if (!isFinite(audio.duration) || isNaN(audio.duration)) {
        // Only log once to avoid spam
        if (!audio._debugLogged) {
            console.warn(`[Audio ${id}] Duration unknown (NaN). ReadyState: ${audio.readyState}. Src: ${audio.src}`);
            audio._debugLogged = true;
        }
        timeDisplay.textContent = "0:00 / Loading...";
        fill.style.width = '0%';
        return;
    }

    const currentTime = audio.currentTime || 0;
    const duration = audio.duration;
    
    const pct = (currentTime / duration) * 100;
    fill.style.width = Math.min(100, Math.max(0, pct)) + '%';
    timeDisplay.textContent = formatTime(currentTime) + ' / ' + formatTime(duration);
}

function initAudioPlayer(id) {
    const audio = document.getElementById(id);
    if (!audio) return;

    // 1. Check if source is empty (common Python rendering bug)
    if (!audio.src) {
        console.error(`[Audio ${id}] No source defined!`);
        return;
    }

    const onMetadataLoaded = () => {
        audio.removeEventListener('loadedmetadata', onMetadataLoaded);
        console.log(`[Audio ${id}] Metadata loaded. Duration: ${audio.duration}s`);
        updateProgress(id);
    };

    // 2. Immediate check for cached/metadata-ready files
    if (audio.readyState >= 1) {
        onMetadataLoaded();
    } else {
        // 3. Wait for metadata
        audio.addEventListener('loadedmetadata', onMetadataLoaded, { once: true });
        
        // 4. FORCE LOAD if stuck (Safety net)
        setTimeout(() => {
            if (isNaN(audio.duration) || !isFinite(audio.duration)) {
                console.warn(`[Audio ${id}] Timeout waiting for metadata. Forcing load()...`);
                audio.load(); 
            }
        }, 1500);
    }

    // Play/Pause Handlers
    const handlePlay = () => {
        const playBtn = audio.parentElement.querySelector('.play-btn');
        if (playBtn) playBtn.classList.add('paused');
        
        document.querySelectorAll('audio').forEach(a => {
            if (a !== audio && !a.paused) {
                a.pause();
                const otherBtn = a.parentElement.querySelector('.play-btn');
                if (otherBtn) otherBtn.classList.remove('paused');
            }
        });
    };

    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', () => {
        const playBtn = audio.parentElement.querySelector('.play-btn');
        if (playBtn) playBtn.classList.remove('paused');
    });

    audio.addEventListener('timeupdate', () => updateProgress(id));
    audio.addEventListener('ended', () => onAudioEnded(id));
    
    // Error handler for broken files
    audio.addEventListener('error', (e) => {
        console.error(`[Audio ${id}] Load error:`, e.target.error);
        const timeDisplay = document.getElementById('time-' + id);
        if(timeDisplay) timeDisplay.textContent = "Error loading file";
    });
}

function toggleAudio(id, playerEl) {
    const audio = document.getElementById(id);
    if (!audio) return;

    // If metadata not loaded, try to trigger it manually
    if (isNaN(audio.duration) || !isFinite(audio.duration)) {
        console.warn(`[Toggle ${id}] Metadata missing. Attempting play anyway...`);
        // Sometimes play() triggers metadata load
        audio.play().catch(e => console.error("Play failed:", e));
        return;
    }

    if (audio.paused) {
        audio.play().catch(e => console.error("Playback failed:", e));
    } else {
        audio.pause();
    }
}

function seekAudio(event, id) {
    event.stopPropagation();
    const audio = document.getElementById(id);
    if (!audio || !isFinite(audio.duration) || isNaN(audio.duration)) return;
    
    const bar = event.currentTarget.querySelector('.progress-bar');
    if (!bar) return;
    
    const rect = bar.getBoundingClientRect();
    let ratio = (event.clientX - rect.left) / rect.width;
    ratio = Math.max(0, Math.min(1, ratio));
    
    audio.currentTime = ratio * audio.duration;
    updateProgress(id);
}

function onAudioEnded(id) {
    const audio = document.getElementById(id);
    if (!audio) return;
    
    const playBtn = audio.parentElement.querySelector('.play-btn');
    if (playBtn) playBtn.classList.remove('paused');
    
    const fill = document.getElementById('fill-' + id);
    if (fill) fill.style.width = '0%';
    
    const timeDisplay = document.getElementById('time-' + id);
    if (timeDisplay) timeDisplay.textContent = formatTime(0) + ' / ' + formatTime(audio.duration);
}

document.addEventListener('DOMContentLoaded', () => {
    const audios = document.querySelectorAll('audio[id^="audio-"]');
    console.log(`[Init] Found ${audios.length} audio players.`);
    audios.forEach(audio => {
        initAudioPlayer(audio.id);
    });
});