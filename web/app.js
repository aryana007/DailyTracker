/**
 * Daily Routine & Food Log - Client Application
 * Communicates with Python backend via REST API
 */

(function () {
  'use strict';

  // Navigation Tabs & Views
  const tabLoggerBtn = document.getElementById('tabLoggerBtn');
  const tabHistoryBtn = document.getElementById('tabHistoryBtn');
  const loggerView = document.getElementById('loggerView');
  const historyView = document.getElementById('historyView');
  const historyCountBadge = document.getElementById('historyCountBadge');

  // Logger Form Elements
  const dateInput = document.getElementById('dateInput');
  const prevDayBtn = document.getElementById('prevDayBtn');
  const todayBtn = document.getElementById('todayBtn');
  const nextDayBtn = document.getElementById('nextDayBtn');
  const dateNoticeBanner = document.getElementById('dateNoticeBanner');

  const wakeUpInput = document.getElementById('wakeUpInput');
  const nowBtn = document.getElementById('nowBtn');

  const runInput = document.getElementById('runInput');
  const runMinus = document.getElementById('runMinus');
  const runPlus = document.getElementById('runPlus');

  const walkInput = document.getElementById('walkInput');
  const walkMinus = document.getElementById('walkMinus');
  const walkPlus = document.getElementById('walkPlus');

  const officeInput = document.getElementById('officeInput');
  const officeMinus = document.getElementById('officeMinus');
  const officePlus = document.getElementById('officePlus');

  const mealCountInput = document.getElementById('mealCountInput');
  const mealMinus = document.getElementById('mealMinus');
  const mealPlus = document.getElementById('mealPlus');

  const chipsListContainer = document.getElementById('chipsListContainer');
  const addCustomChipBtn = document.getElementById('addCustomChipBtn');
  const foodTextInput = document.getElementById('foodTextInput');

  // KPI Glance Elements
  const kpiMovement = document.getElementById('kpiMovement');
  const kpiOffice = document.getElementById('kpiOffice');
  const kpiMeals = document.getElementById('kpiMeals');

  // Action Buttons
  const saveLocalBtn = document.getElementById('saveLocalBtn');
  const syncGoogleBtn = document.getElementById('syncGoogleBtn');
  const syncBtnText = document.getElementById('syncBtnText');
  const openSheetBtn = document.getElementById('openSheetBtn');
  const openSheetSecondaryBtn = document.getElementById('openSheetSecondaryBtn');
  const exportCsvBtn = document.getElementById('exportCsvBtn');

  // Status Indicators
  const queueStatusText = document.getElementById('queueStatusText');
  const queueIndicatorDot = document.getElementById('queueIndicatorDot');
  const liveStatusText = document.getElementById('liveStatusText');
  const cloudStatusBadge = document.getElementById('cloudStatusBadge');

  // History & Trend Elements
  const trendChartBars = document.getElementById('trendChartBars');
  const weeklyMovementTotal = document.getElementById('weeklyMovementTotal');
  const historyCardsContainer = document.getElementById('historyCardsContainer');
  const historyTotalLabel = document.getElementById('historyTotalLabel');

  // Toast & Modals
  const toastNotification = document.getElementById('toastNotification');
  const toastIcon = document.getElementById('toastIcon');
  const toastMessage = document.getElementById('toastMessage');

  const themeToggleBtn = document.getElementById('themeToggleBtn');
  const sunIcon = themeToggleBtn.querySelector('.sun-icon');
  const moonIcon = themeToggleBtn.querySelector('.moon-icon');

  const helpBtn = document.getElementById('helpBtn');
  const helpModal = document.getElementById('helpModal');
  const closeHelpModal = document.getElementById('closeHelpModal');
  const dismissHelpModalBtn = document.getElementById('dismissHelpModalBtn');

  let toastTimer = null;
  let isSyncing = false;
  let userSettings = { quick_chips: [] };

  // --- API Abstraction ---
  async function callBackend(endpoint, method = 'GET', body = null) {
    try {
      const options = {
        method: method,
        headers: { 'Content-Type': 'application/json' },
      };
      if (body) options.body = JSON.stringify(body);
      const res = await fetch(endpoint, options);
      return await res.json();
    } catch (err) {
      console.warn('Backend call failed:', err);
      return { error: err.message };
    }
  }

  // --- Toast Notifications ---
  function showToast(message, isError = false, duration = 3000) {
    if (toastTimer) clearTimeout(toastTimer);
    toastIcon.textContent = isError ? '⚠️' : '✓';
    toastMessage.textContent = message;
    toastNotification.style.borderColor = isError ? '#EF4444' : 'rgba(255,255,255,0.18)';
    toastNotification.classList.remove('hidden');

    toastTimer = setTimeout(() => {
      toastNotification.classList.add('hidden');
    }, duration);
  }

  toastNotification.addEventListener('click', () => {
    toastNotification.classList.add('hidden');
  });

  // --- Date Operations & Smart Auto-Fill ---
  function formatDate(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  async function checkDateAutoFill(targetDate) {
    if (!targetDate) return;
    const res = await callBackend(`/api/entry?date=${targetDate}`);
    if (res && res.found && res.entry) {
      const e = res.entry;
      wakeUpInput.value = e.wake_up || '';
      runInput.value = e.run_time || '0';
      walkInput.value = e.walk_time || '0';
      officeInput.value = e.office_time || '0';
      mealCountInput.value = e.meal_count || '0';
      foodTextInput.value = e.food_details === 'None logged' ? '' : (e.food_details || '');
      updateKpis();
      dateNoticeBanner.classList.remove('hidden');
      dateNoticeBanner.textContent = `ℹ️ Loaded existing record for ${targetDate} (edit mode)`;
    } else {
      dateNoticeBanner.classList.add('hidden');
      // If no entry exists and we switched dates, don't wipe everything if it's today on first load
    }
  }

  function setToday() {
    dateInput.value = formatDate(new Date());
    checkDateAutoFill(dateInput.value);
    showToast('Date reset to Today');
  }

  function shiftDate(days) {
    const parts = dateInput.value.split('-');
    let cur = new Date();
    if (parts.length === 3) {
      cur = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    }
    cur.setDate(cur.getDate() + days);
    dateInput.value = formatDate(cur);
    checkDateAutoFill(dateInput.value);
    showToast(`Date set to ${cur.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}`);
  }

  prevDayBtn.addEventListener('click', () => shiftDate(-1));
  nextDayBtn.addEventListener('click', () => shiftDate(1));
  todayBtn.addEventListener('click', setToday);
  dateInput.addEventListener('change', () => checkDateAutoFill(dateInput.value));

  // --- Wake Up Time Presets ---
  function formatAMPM(date) {
    let hours = date.getHours();
    let minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;
    return `${String(hours).padStart(2, '0')}:${minutes} ${ampm}`;
  }

  nowBtn.addEventListener('click', () => {
    const timeStr = formatAMPM(new Date());
    wakeUpInput.value = timeStr;
    showToast(`Wake Up set to ${timeStr}`);
  });

  document.querySelectorAll('.preset-wake').forEach(btn => {
    btn.addEventListener('click', () => {
      wakeUpInput.value = btn.dataset.time;
      showToast(`Wake Up set to ${btn.dataset.time}`);
    });
  });

  // --- Stepper Utilities ---
  function updateKpis() {
    const run = parseFloat(runInput.value) || 0;
    const walk = parseFloat(walkInput.value) || 0;
    const office = parseFloat(officeInput.value) || 0;
    const meals = parseInt(mealCountInput.value) || 0;

    const totalMove = Math.round(run + walk);
    kpiMovement.textContent = `${totalMove}m`;
    kpiOffice.textContent = `${office.toFixed(1).replace(/\.0$/, '')}h`;
    kpiMeals.textContent = `${meals}`;
  }

  function setupStepper(inputEl, minusBtn, plusBtn, step, isFloat = false) {
    minusBtn.addEventListener('click', () => {
      let cur = parseFloat(inputEl.value) || 0;
      let next = Math.max(0, cur - step);
      inputEl.value = isFloat ? next.toFixed(1).replace(/\.0$/, '') : Math.round(next);
      updateKpis();
    });

    plusBtn.addEventListener('click', () => {
      let cur = parseFloat(inputEl.value) || 0;
      let next = cur + step;
      inputEl.value = isFloat ? next.toFixed(1).replace(/\.0$/, '') : Math.round(next);
      updateKpis();
    });

    inputEl.addEventListener('input', updateKpis);
  }

  setupStepper(runInput, runMinus, runPlus, 5, false);
  setupStepper(walkInput, walkMinus, walkPlus, 5, false);
  setupStepper(officeInput, officeMinus, officePlus, 0.5, true);
  setupStepper(mealCountInput, mealMinus, mealPlus, 1, false);

  // Quick preset pills
  document.querySelectorAll('.preset-run').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseFloat(btn.dataset.val);
      runInput.value = (parseFloat(runInput.value) || 0) + val;
      updateKpis();
    });
  });

  document.querySelectorAll('.preset-walk').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseFloat(btn.dataset.val);
      walkInput.value = (parseFloat(walkInput.value) || 0) + val;
      updateKpis();
    });
  });

  document.querySelectorAll('.preset-office').forEach(btn => {
    btn.addEventListener('click', () => {
      const val = parseFloat(btn.dataset.val);
      officeInput.value = val;
      updateKpis();
    });
  });

  // --- Dynamic Quick Meal Chips ---
  function renderChips(chipsArray) {
    chipsListContainer.innerHTML = '';
    chipsArray.forEach(meal => {
      const btn = document.createElement('button');
      btn.className = 'chip-btn';
      btn.textContent = `+ ${meal}`;
      btn.addEventListener('click', () => {
        const current = foodTextInput.value.trim();
        const cleanName = meal.replace(/^[^\w\s]+/, '').trim();
        if (!current) {
          foodTextInput.value = cleanName;
        } else {
          const sep = current.endsWith(',') || current.endsWith(';') ? ' ' : ', ';
          foodTextInput.value = current + sep + cleanName;
        }
        if ((parseInt(mealCountInput.value) || 0) === 0) {
          mealCountInput.value = '1';
          updateKpis();
        }
        showToast(`Added + ${cleanName}`);
      });
      chipsListContainer.appendChild(btn);
    });
  }

  addCustomChipBtn.addEventListener('click', async () => {
    const newName = prompt('Enter name of new quick meal or snack (e.g. 🥤 Protein Shake):');
    if (newName && newName.trim()) {
      const clean = newName.trim();
      if (!userSettings.quick_chips.includes(clean)) {
        userSettings.quick_chips.push(clean);
        renderChips(userSettings.quick_chips);
        await callBackend('/api/settings', 'POST', userSettings);
        showToast(`Saved custom chip: ${clean}`);
      }
    }
  });

  // --- Form Collection & Reset ---
  function getFormData() {
    const dateVal = dateInput.value.trim();
    const wakeUpVal = wakeUpInput.value.trim();
    const foodDetails = foodTextInput.value.trim().replace(/\n/g, '; ');

    if (!dateVal || !wakeUpVal) {
      return null;
    }

    return {
      date: dateVal,
      wake_up: wakeUpVal,
      run_time: runInput.value.trim() || '0',
      walk_time: walkInput.value.trim() || '0',
      office_time: officeInput.value.trim() || '0',
      meal_count: mealCountInput.value.trim() || '0',
      food_details: foodDetails || 'None logged',
    };
  }

  function clearForm() {
    setToday();
    wakeUpInput.value = '';
    runInput.value = '0';
    walkInput.value = '0';
    officeInput.value = '0';
    mealCountInput.value = '0';
    foodTextInput.value = '';
    dateNoticeBanner.classList.add('hidden');
    updateKpis();
  }

  // --- Queue & Status Updates ---
  function updateQueueUI(count, totalHistory = 0) {
    if (count > 0) {
      queueIndicatorDot.className = 'status-dot dot-amber';
      queueStatusText.textContent = `${count} unsynced log${count > 1 ? 's' : ''} stored offline`;
      cloudStatusBadge.className = 'badge-status text-amber';
      cloudStatusBadge.textContent = `${count} Queued`;
    } else {
      queueIndicatorDot.className = 'status-dot dot-green';
      queueStatusText.textContent = 'Local Queue: All synced';
      cloudStatusBadge.className = 'badge-status';
      cloudStatusBadge.textContent = 'Ready';
    }
    historyCountBadge.textContent = totalHistory || 0;
  }

  async function refreshStatus() {
    const res = await callBackend('/api/status');
    if (res && res.queue_count !== undefined) {
      updateQueueUI(res.queue_count, res.total_history);
    }
  }

  // --- Save Offline Action ---
  async function saveLocally() {
    if (isSyncing) return;
    const form = getFormData();
    if (!form) {
      showToast('Please enter at least Date and Wake Up Time', true);
      return;
    }

    saveLocalBtn.disabled = true;
    const res = await callBackend('/api/save', 'POST', form);
    saveLocalBtn.disabled = false;

    if (res && res.success) {
      updateQueueUI(res.queue_count);
      liveStatusText.textContent = 'Saved to queue';
      liveStatusText.className = 'status-right text-accent';
      showToast('✓ Entry saved offline to local queue!');
      refreshHistory();
    } else {
      showToast(res.error || 'Failed to save locally', true);
    }
  }

  // --- Sync to Google Sheets Action ---
  async function syncToGoogle() {
    if (isSyncing) return;

    const form = getFormData();
    const status = await callBackend('/api/status');
    const queueCount = status.queue_count || 0;

    if (!form && queueCount === 0) {
      showToast('Nothing to sync. Fill form or save locally first', true);
      return;
    }

    isSyncing = true;
    syncGoogleBtn.disabled = true;
    syncBtnText.textContent = '⏳ Syncing...';
    liveStatusText.textContent = 'Syncing...';
    liveStatusText.className = 'status-right text-amber';
    showToast('Connecting to Google Sheets...');

    const payload = form ? { current: form } : {};
    const res = await callBackend('/api/sync', 'POST', payload);

    isSyncing = false;
    syncGoogleBtn.disabled = false;
    syncBtnText.textContent = '☁️ Sync to Sheets';

    if (res && res.success) {
      updateQueueUI(0);
      liveStatusText.textContent = 'Synced';
      liveStatusText.className = 'status-right text-emerald';
      showToast(`✓ Synced ${res.count} entry/entries to Google Sheets!`, false, 4000);
      refreshHistory();
    } else {
      liveStatusText.textContent = 'Sync failed';
      liveStatusText.className = 'status-right text-amber';
      showToast(res.error || 'Sync failed. Check credentials or network', true, 5000);
      alert(`Google Sheets Sync Failed:\n\n${res.error || 'Unknown error'}`);
    }
  }

  // --- Open Google Sheet ---
  async function openGoogleSheet() {
    showToast('Opening Google Sheet in your browser...');
    await callBackend('/api/open_sheet', 'POST');
  }

  // --- Export CSV ---
  function exportCsv() {
    window.location.href = '/api/export_csv';
    showToast('Downloading CSV export...');
  }

  saveLocalBtn.addEventListener('click', saveLocally);
  syncGoogleBtn.addEventListener('click', syncToGoogle);
  openSheetBtn.addEventListener('click', openGoogleSheet);
  openSheetSecondaryBtn.addEventListener('click', openGoogleSheet);
  exportCsvBtn.addEventListener('click', exportCsv);

  // --- History & Analytics View Rendering ---
  async function refreshHistory() {
    const res = await callBackend('/api/history');
    if (!res || !res.history) return;

    const history = res.history;
    historyTotalLabel.textContent = `${history.length} log${history.length !== 1 ? 's' : ''}`;
    historyCountBadge.textContent = history.length;

    // Render Past 7-Day Activity Chart
    const past7Days = history.slice(0, 7).reverse();
    trendChartBars.innerHTML = '';
    let weekTotalMove = 0;
    const maxVal = Math.max(...past7Days.map(d => (parseFloat(d.run_time) || 0) + (parseFloat(d.walk_time) || 0)), 45);

    past7Days.forEach(day => {
      const move = (parseFloat(day.run_time) || 0) + (parseFloat(day.walk_time) || 0);
      weekTotalMove += move;
      const pct = Math.max(10, Math.min(100, Math.round((move / maxVal) * 100)));

      const col = document.createElement('div');
      col.className = 'chart-col';
      col.innerHTML = `
        <div class="bar-track" title="${day.date}: ${move}m active">
          <div class="bar-fill" style="height: ${pct}%;"></div>
        </div>
        <span class="bar-label">${day.date.slice(5)}</span>
      `;
      trendChartBars.appendChild(col);
    });
    weeklyMovementTotal.textContent = `${weekTotalMove}m total`;

    // Render Past Days List
    historyCardsContainer.innerHTML = '';
    if (history.length === 0) {
      historyCardsContainer.innerHTML = '<div class="history-empty-state">No previous logs found. Log your first day above!</div>';
      return;
    }

    history.forEach(item => {
      const card = document.createElement('div');
      card.className = 'history-item-card';
      const moveTotal = Math.round((parseFloat(item.run_time) || 0) + (parseFloat(item.walk_time) || 0));
      const syncStatusTag = item.synced ? '🟢 Synced' : '🟠 Queued';

      card.innerHTML = `
        <div class="history-item-left">
          <div class="history-date-badge">${item.date} <span class="text-xs font-normal text-muted">${syncStatusTag}</span></div>
          <div class="history-summary-stats">
            <span>🏃 ${moveTotal}m</span>
            <span>💼 ${item.office_time || 0}h</span>
            <span>🍽️ ${item.meal_count || 0} meals</span>
            <span>⏰ ${item.wake_up || '—'}</span>
          </div>
          <div class="history-food-snippet">${item.food_details || 'No food notes'}</div>
        </div>
        <button class="btn-edit-day" data-date="${item.date}">✏️ Edit</button>
      `;

      card.querySelector('.btn-edit-day').addEventListener('click', () => {
        dateInput.value = item.date;
        checkDateAutoFill(item.date);
        switchTab('logger');
        showToast(`Loaded ${item.date} into editor`);
      });

      historyCardsContainer.appendChild(card);
    });
  }

  // --- Navigation Tab Switching ---
  function switchTab(target) {
    if (target === 'logger') {
      tabLoggerBtn.classList.add('active');
      tabHistoryBtn.classList.remove('active');
      loggerView.classList.remove('hidden');
      historyView.classList.add('hidden');
    } else {
      tabHistoryBtn.classList.add('active');
      tabLoggerBtn.classList.remove('active');
      historyView.classList.remove('hidden');
      loggerView.classList.add('hidden');
      refreshHistory();
    }
  }

  tabLoggerBtn.addEventListener('click', () => switchTab('logger'));
  tabHistoryBtn.addEventListener('click', () => switchTab('history'));

  // --- Keyboard Shortcuts ---
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveLocally();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      syncToGoogle();
    }
  });

  // --- Dark / Light Theme Toggle ---
  function initTheme() {
    const saved = localStorage.getItem('daily_tracker_theme') || 'dark';
    if (saved === 'light') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      sunIcon.classList.remove('hidden');
      moonIcon.classList.add('hidden');
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
      sunIcon.classList.add('hidden');
      moonIcon.classList.remove('hidden');
    }
  }

  themeToggleBtn.addEventListener('click', () => {
    const isDark = document.documentElement.classList.contains('dark');
    if (isDark) {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      localStorage.setItem('daily_tracker_theme', 'light');
      sunIcon.classList.remove('hidden');
      moonIcon.classList.add('hidden');
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
      localStorage.setItem('daily_tracker_theme', 'dark');
      sunIcon.classList.add('hidden');
      moonIcon.classList.remove('hidden');
    }
  });

  // --- Help Modal ---
  helpBtn.addEventListener('click', () => helpModal.classList.remove('hidden'));
  closeHelpModal.addEventListener('click', () => helpModal.classList.add('hidden'));
  dismissHelpModalBtn.addEventListener('click', () => helpModal.classList.add('hidden'));
  helpModal.addEventListener('click', (e) => {
    if (e.target === helpModal) helpModal.classList.add('hidden');
  });

  // --- Startup Initialization ---
  async function initApp() {
    initTheme();
    setToday();
    updateKpis();

    // Fetch user settings (custom chips)
    const setRes = await callBackend('/api/settings');
    if (setRes && setRes.settings) {
      userSettings = setRes.settings;
      renderChips(userSettings.quick_chips || []);
    }

    refreshStatus();
    refreshHistory();
  }

  initApp();

})();
