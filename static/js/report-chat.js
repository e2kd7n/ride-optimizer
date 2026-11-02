/**
 * report-chat.js — "Ask about your rides" chat on the Reports page (#608)
 *
 * The conversation lives only in this tab: the transcript is kept in
 * sessionStorage so it survives a reload, and is sent whole to /api/chat on
 * each turn (the server stores nothing). Closing the tab or "New chat" ends it.
 */
(function () {
    const STORAGE_KEY = 'rideChat.v1';
    const EXAMPLES = [
        'How many miles did I ride this month vs. the same month last year?',
        'Which bike has the most miles this year?',
        "What's my longest ride on a weekday?",
        'Which day of the week do I ride most?',
    ];

    const chatApi = new APIClient('/api');
    let messages = [];      // [{role: 'user'|'assistant', content: string}]
    let busy = false;
    let configured = false;

    let logEl, formEl, inputEl, sendBtn, newBtn, examplesEl, disabledEl;

    document.addEventListener('DOMContentLoaded', () => {
        logEl = document.getElementById('chat-log');
        if (!logEl) return;
        formEl = document.getElementById('chat-form');
        inputEl = document.getElementById('chat-input');
        sendBtn = document.getElementById('chat-send-btn');
        newBtn = document.getElementById('chat-new-btn');
        examplesEl = document.getElementById('chat-examples');
        disabledEl = document.getElementById('chat-disabled');

        messages = loadTranscript();
        formEl.addEventListener('submit', (e) => {
            e.preventDefault();
            send(inputEl.value);
        });
        inputEl.addEventListener('keydown', (e) => {
            // Enter sends; Shift+Enter adds a line.
            if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
                e.preventDefault();
                send(inputEl.value);
            }
        });
        inputEl.addEventListener('input', autoGrow);
        newBtn.addEventListener('click', newChat);

        if (messages.length) {
            // Reopen a chat that's still in progress after a reload.
            const panel = document.getElementById('ride-chat-panel');
            if (panel && window.bootstrap) bootstrap.Collapse.getOrCreateInstance(panel, { toggle: false }).show();
        }
        render();
        checkStatus();
    });

    // -------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------
    function loadTranscript() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            const parsed = raw ? JSON.parse(raw) : [];
            return Array.isArray(parsed) ? parsed.filter(m =>
                m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string') : [];
        } catch (_) {
            return [];
        }
    }

    function saveTranscript() {
        try {
            if (messages.length) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
            else sessionStorage.removeItem(STORAGE_KEY);
        } catch (_) { /* storage unavailable: the chat still works for this page view */ }
    }

    async function checkStatus() {
        try {
            const res = await chatApi.getChatStatus();
            configured = !!res.configured;
        } catch (_) {
            configured = false;
        }
        if (!configured) {
            disabledEl.innerHTML = '<i class="bi bi-info-circle" aria-hidden="true"></i> ' +
                "Ride chat isn't set up. Add <code>ANTHROPIC_API_KEY</code> to the server's <code>.env</code> and restart to enable it.";
            disabledEl.classList.remove('d-none');
        }
        updateControls();
    }

    function newChat() {
        if (busy) return;
        messages = [];
        saveTranscript();
        render();
        inputEl.focus();
    }

    // -------------------------------------------------------------------
    // Sending
    // -------------------------------------------------------------------
    async function send(text) {
        const content = (text || '').trim();
        if (!content || busy || !configured) return;

        messages.push({ role: 'user', content });
        inputEl.value = '';
        autoGrow();
        busy = true;
        saveTranscript();
        render();
        const thinking = appendBubble('assistant', null, 'chat-msg-thinking');
        thinking.innerHTML = '<span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Looking at your rides…';
        scrollToEnd();

        try {
            const res = await chatApi.sendChatMessage(messages);
            messages.push({ role: 'assistant', content: res.reply || '' });
            saveTranscript();
            busy = false;
            render();
        } catch (err) {
            // Drop the unanswered question from the transcript and hand it
            // back to the input so it can be retried as-is.
            messages.pop();
            saveTranscript();
            busy = false;
            render();
            inputEl.value = content;
            autoGrow();
            if (err.status === 503) {
                configured = false;
                checkStatus();
            }
            const msg = err.name === 'AbortError'
                ? 'That took too long. Try again or ask a narrower question.'
                : (err.message || 'Something went wrong. Try again.');
            appendBubble('assistant', null, 'chat-msg-error').textContent = msg;
        }
        scrollToEnd();
        inputEl.focus();
    }

    // -------------------------------------------------------------------
    // Rendering
    // -------------------------------------------------------------------
    function render() {
        logEl.innerHTML = '';
        messages.forEach(m => appendBubble(m.role, m.content));
        renderExamples();
        updateControls();
        scrollToEnd();
    }

    function appendBubble(role, content, extraClass) {
        const div = document.createElement('div');
        div.className = `chat-msg chat-msg-${role}` + (extraClass ? ` ${extraClass}` : '');
        if (content !== null && content !== undefined) {
            if (role === 'assistant') div.innerHTML = renderMarkdown(content);
            else div.textContent = content;
        }
        logEl.appendChild(div);
        return div;
    }

    function renderExamples() {
        examplesEl.innerHTML = '';
        if (messages.length || !configured) return;
        EXAMPLES.forEach(q => {
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'btn btn-outline-primary btn-sm fs-11';
            b.textContent = q;
            b.addEventListener('click', () => send(q));
            examplesEl.appendChild(b);
        });
    }

    function updateControls() {
        const off = busy || !configured;
        inputEl.disabled = !configured;
        sendBtn.disabled = off;
        newBtn.classList.toggle('d-none', messages.length === 0);
        newBtn.disabled = busy;
        if (!messages.length) renderExamples();
    }

    function scrollToEnd() {
        logEl.scrollTop = logEl.scrollHeight;
    }

    function autoGrow() {
        inputEl.style.height = 'auto';
        inputEl.style.height = `${inputEl.scrollHeight}px`;
    }

    // -------------------------------------------------------------------
    // Minimal markdown: paragraphs, lists, tables, code, bold/italic.
    // Input is HTML-escaped first, so nothing from the reply can inject markup.
    // -------------------------------------------------------------------
    function renderInline(s) {
        return s
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/(^|[^*\w])\*([^*\n]+)\*(?!\w)/g, '$1<em>$2</em>')
            .replace(/(^|[^_\w])_([^_\n]+)_(?!\w)/g, '$1<em>$2</em>');
    }

    function renderMarkdown(text) {
        const lines = escapeHtml(text).split('\n');
        const out = [];
        let i = 0;
        const isTableRow = l => /^\s*\|.*\|\s*$/.test(l);
        const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => renderInline(c.trim()));

        while (i < lines.length) {
            const line = lines[i];
            if (/^\s*```/.test(line)) {
                const code = [];
                i++;
                while (i < lines.length && !/^\s*```/.test(lines[i])) code.push(lines[i++]);
                i++;
                out.push(`<pre><code>${code.join('\n')}</code></pre>`);
            } else if (isTableRow(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
                const head = cells(line);
                i += 2;
                const rows = [];
                while (i < lines.length && isTableRow(lines[i])) rows.push(cells(lines[i++]));
                out.push('<div class="table-responsive"><table><thead><tr>' +
                    head.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>' +
                    rows.map(r => '<tr>' + r.map(c => `<td>${c}</td>`).join('') + '</tr>').join('') +
                    '</tbody></table></div>');
            } else if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
                const ordered = /^\s*\d+\./.test(line);
                const items = [];
                while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
                    items.push(renderInline(lines[i++].replace(/^\s*([-*]|\d+\.)\s+/, '')));
                }
                const tag = ordered ? 'ol' : 'ul';
                out.push(`<${tag}>` + items.map(it => `<li>${it}</li>`).join('') + `</${tag}>`);
            } else if (/^\s*#{1,6}\s+/.test(line)) {
                out.push(`<p><strong>${renderInline(line.replace(/^\s*#{1,6}\s+/, ''))}</strong></p>`);
                i++;
            } else if (!line.trim()) {
                i++;
            } else {
                const para = [];
                while (i < lines.length && lines[i].trim() && !/^\s*(```|[-*]\s|\d+\.\s|#{1,6}\s)/.test(lines[i]) &&
                       !isTableRow(lines[i])) {
                    para.push(renderInline(lines[i++]));
                }
                if (!para.length) para.push(renderInline(lines[i++]));
                out.push(`<p>${para.join('<br>')}</p>`);
            }
        }
        return out.join('');
    }

})();
