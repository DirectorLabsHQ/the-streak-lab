// js/streak-tracker.js
// Upgraded shared streak tracker for The Streak Lab experiments
// Features: current/longest streak, stats, future-day lock, notes, reset, export
// Config via data attributes on any element (e.g. <div data-experiment-key="...">)

document.addEventListener('DOMContentLoaded', () => {

  // ── Configuration ─────────────────────────────────────────────────────────
  // Look for data attributes on any element; fallback to defaults
  const configEl = document.querySelector('[data-experiment-key]') || document.body;

  const EXPERIMENT_KEY  = configEl.dataset.experimentKey  || 'default-experiment';
  const TOTAL_DAYS      = parseInt(configEl.dataset.totalDays    || '30', 10);
  const EXPERIMENT_NAME = configEl.dataset.experimentName || 'Habit Experiment';

  let streakData = {
    startDate: null,
    completed: [],     // day numbers 1..30
    missed:    [],     // day numbers
    notes:     {}      // { day: "note text" }
  };

  // ── Data Management ───────────────────────────────────────────────────────

  function loadData() {
    const saved = localStorage.getItem(EXPERIMENT_KEY);
    if (saved) {
      streakData = JSON.parse(saved);
      if (streakData.startDate) streakData.startDate = new Date(streakData.startDate);
    }
    // Auto-start if never used
    if (!streakData.startDate) {
      streakData.startDate = new Date();
      streakData.startDate.setHours(0, 0, 0, 0);
      saveData();
    }
  }

  function saveData() {
    localStorage.setItem(EXPERIMENT_KEY, JSON.stringify(streakData));
  }

  // ── Date & Streak Calculations ────────────────────────────────────────────

  function getCurrentDay() {
    if (!streakData.startDate) return 0;
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const diffMs = now - streakData.startDate;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    return Math.min(diffDays + 1, TOTAL_DAYS);
  }

  function calculateCurrentStreak() {
    let streak = 0;
    const today = getCurrentDay();
    for (let d = today; d >= 1; d--) {
      if (streakData.completed.includes(d)) streak++;
      else break;
    }
    return streak;
  }

  function calculateLongestStreak() {
    let max = 0;
    let current = 0;
    for (let d = 1; d <= TOTAL_DAYS; d++) {
      if (streakData.completed.includes(d)) {
        current++;
        max = Math.max(max, current);
      } else {
        current = 0;
      }
    }
    return max;
  }

  function updateStats() {
    const today = getCurrentDay();
    const completedCount = streakData.completed.length;
    const percent = TOTAL_DAYS > 0 ? Math.round((completedCount / TOTAL_DAYS) * 100) : 0;
    const daysElapsed = Math.min(today, TOTAL_DAYS);

    const els = {
      currentStreak:  document.getElementById('current-streak'),
      longestStreak:  document.getElementById('longest-streak'),
      percentComplete: document.getElementById('percent-complete'),
      daysElapsed:    document.getElementById('days-elapsed')
    };

    if (els.currentStreak)  els.currentStreak.textContent  = calculateCurrentStreak();
    if (els.longestStreak)  els.longestStreak.textContent  = calculateLongestStreak();
    if (els.percentComplete) els.percentComplete.textContent = percent;
    if (els.daysElapsed)    els.daysElapsed.textContent    = daysElapsed;
  }

  // ── Calendar ──────────────────────────────────────────────────────────────

  function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    if (!grid) return;

    grid.innerHTML = '';
    const currentDay = getCurrentDay();

    for (let day = 1; day <= TOTAL_DAYS; day++) {
      const dayEl = document.createElement('div');
      dayEl.className = 'day';
      dayEl.textContent = day;
      dayEl.setAttribute('aria-label', `Day ${day}${day === currentDay ? ' (today)' : ''}${day > currentDay ? ' (future)' : ''}`);

      if (streakData.completed.includes(day)) dayEl.classList.add('completed');
      if (streakData.missed.includes(day))    dayEl.classList.add('missed');
      if (streakData.notes[day])              dayEl.classList.add('has-note');
      if (day === currentDay)                 dayEl.classList.add('today');
      if (day > currentDay)                   dayEl.classList.add('future');

      // Only allow clicks on past + today
      dayEl.onclick = () => {
        if (day <= currentDay) toggleDay(day);
      };

      grid.appendChild(dayEl);
    }

    updateStats();
  }

  // ── Interactions ──────────────────────────────────────────────────────────

  function toggleDay(day) {
    if (streakData.completed.includes(day)) {
      streakData.completed = streakData.completed.filter(d => d !== day);
      streakData.missed.push(day);
    } else if (streakData.missed.includes(day)) {
      streakData.missed = streakData.missed.filter(d => d !== day);
    } else {
      streakData.completed.push(day);
    }

    streakData.completed.sort((a,b) => a - b);
    streakData.missed.sort((a,b) => a - b);

    saveData();
    renderCalendar();

    // Show note editor
    const noteDayEl   = document.getElementById('note-day');
    const noteInput   = document.getElementById('note-input');
    const noteSection = document.getElementById('note-section');

    if (noteDayEl && noteInput && noteSection) {
      noteDayEl.textContent = day;
      noteInput.value = streakData.notes[day] || '';
      noteSection.style.display = 'block';
      noteInput.focus();
    }
  }

  window.saveNote = function() {
    const dayStr = document.getElementById('note-day')?.textContent;
    const day = dayStr ? parseInt(dayStr, 10) : null;
    const text = document.getElementById('note-input')?.value.trim();

    if (day && text !== undefined) {
      if (text) {
        streakData.notes[day] = text;
      } else {
        delete streakData.notes[day];
      }
      saveData();
      renderCalendar();
    }
  };

  window.resetTracker = function() {
    if (confirm(`Reset ${EXPERIMENT_NAME}? All data will be cleared permanently.`)) {
      localStorage.removeItem(EXPERIMENT_KEY);
      streakData = {
        startDate: new Date(),
        completed: [], missed: [], notes: {}
      };
      streakData.startDate.setHours(0,0,0,0);
      saveData();
      document.getElementById('note-section')?.style.setProperty('display', 'none');
      renderCalendar();
    }
  };

  window.exportSummary = function() {
    const today = getCurrentDay();
    const lines = [
      `${EXPERIMENT_NAME} Summary`,
      `Started: ${streakData.startDate ? streakData.startDate.toDateString() : 'N/A'}`,
      `Current day: ${today} / ${TOTAL_DAYS}`,
      `Current streak: ${calculateCurrentStreak()} days`,
      `Longest streak: ${calculateLongestStreak()} days`,
      `Completion: ${Math.round((streakData.completed.length / TOTAL_DAYS) * 100)}% (${streakData.completed.length}/${TOTAL_DAYS})`,
      ``,
      `Completed days: ${streakData.completed.join(', ') || 'None'}`,
      `Missed days:    ${streakData.missed.join(', ') || 'None'}`,
      ``,
      `Notes:`
    ];

    Object.entries(streakData.notes)
      .sort(([a], [b]) => Number(a) - Number(b))
      .forEach(([day, note]) => lines.push(`Day ${day}: ${note}`));

    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${EXPERIMENT_KEY.replace(/[^a-z0-9]/gi, '-')}-summary.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Start ─────────────────────────────────────────────────────────────────
  loadData();
  renderCalendar();
});