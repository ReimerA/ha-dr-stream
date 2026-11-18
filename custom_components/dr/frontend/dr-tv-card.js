/*
 * DR TV dashboard card.
 *
 * Shows DR's live channels with what is on now, and plays the selected
 * channel inside the card. Data comes from the integration's websocket
 * command `dr/channels`; video is played with hls.js (bundled with the
 * integration) or natively where the browser supports HLS (Safari, iOS).
 *
 *   type: custom:dr-tv-card
 *   channel: dr1        # optional: channel selected at start (id or name)
 *   autoplay: false     # optional: start playing (muted) when shown
 */

const VERSION = new URL(import.meta.url).searchParams.get("v") || "dev";
const HLS_URL = `/dr/hls.min.js?v=${VERSION}`;
const REFRESH_MS = 60_000;

let hlsPromise;
function loadHls() {
  if (window.Hls) return Promise.resolve(window.Hls);
  hlsPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = HLS_URL;
    script.onload = () => resolve(window.Hls);
    script.onerror = () => {
      hlsPromise = undefined;
      reject(new Error("Could not load the video player"));
    };
    document.head.append(script);
  });
  return hlsPromise;
}

/** Small helper: create an element with properties and children. */
function el(tag, props = {}, ...children) {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter((c) => c != null));
  return node;
}

class DrTvCard extends HTMLElement {
  setConfig(config) {
    // Home Assistant may call setConfig again with the same config; only a
    // changed start channel should reset what the viewer picked.
    if (this._config?.channel !== config.channel) {
      this._selectedId = undefined; // resolved from config once channels load
    }
    this._config = { autoplay: false, ...config };
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._refresh();
  }

  connectedCallback() {
    this._build();
    clearInterval(this._timer);
    this._timer = setInterval(() => this._refresh(), REFRESH_MS);
    if (this._hass) this._refresh();
  }

  disconnectedCallback() {
    // Home Assistant sometimes detaches and re-attaches cards while laying
    // out a dashboard. Only stop the stream if the card is really gone.
    setTimeout(() => {
      if (this.isConnected) return;
      clearInterval(this._timer);
      this._stop();
    }, 1000);
  }

  getCardSize() {
    return 9;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getStubConfig() {
    return {};
  }

  // --- data ----------------------------------------------------------------

  async _refresh() {
    if (!this._hass || !this.isConnected) return;
    try {
      const { channels } = await this._hass.callWS({ type: "dr/channels" });
      this._channels = channels;
      this._error = undefined;
    } catch (err) {
      this._error =
        err?.code === "unknown_command" || err?.code === "not_loaded"
          ? "DR TV & Radio is not set up. Add it under Settings → Devices & services."
          : `Could not load DR channels: ${err?.message ?? err}`;
    }
    if (this._selectedId === undefined && this._channels?.length) {
      const wanted = String(this._config.channel ?? "").toLowerCase();
      const match = this._channels.find(
        (c) =>
          c.slug === wanted || c.id === wanted || c.title.toLowerCase() === wanted
      );
      this._selectedId = (match ?? this._channels[0]).id;
      if (this._config.autoplay) this._play(true);
    }
    this._render();
  }

  get _selected() {
    return this._channels?.find((c) => c.id === this._selectedId);
  }

  // --- playback --------------------------------------------------------------

  async _play(muted = false) {
    const channel = this._selected;
    if (!channel) return;
    this._stop();
    this._playingId = channel.id;
    this._playError = undefined;
    const video = this._els.video;
    video.muted = muted;
    this._render();

    try {
      const Hls = await loadHls();
      if (this._playingId !== channel.id) return; // switched meanwhile
      if (Hls.isSupported()) {
        const hls = new Hls({ liveDurationInfinity: true });
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) this._fail(`Playback stopped (${data.details})`);
        });
        hls.loadSource(channel.stream_url);
        hls.attachMedia(video);
        this._hls = hls;
      } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = channel.stream_url;
      } else {
        throw new Error("This browser cannot play live TV streams");
      }
      await video.play();
    } catch (err) {
      // Browsers block autoplay with sound; the controls are still there.
      if (err?.name !== "NotAllowedError") this._fail(err?.message ?? err);
    }
  }

  _stop() {
    this._hls?.destroy();
    this._hls = undefined;
    this._playingId = undefined;
    const video = this._els?.video;
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
  }

  _fail(message) {
    this._stop();
    this._playError = String(message);
    this._render();
  }

  _select(channel) {
    if (channel.id === this._playingId) return;
    this._selectedId = channel.id;
    this._play();
  }

  // --- rendering -------------------------------------------------------------

  _build() {
    if (this._els) return;
    const root = this.attachShadow({ mode: "open" });
    const video = el("video", { controls: true, playsInline: true });
    const poster = el("button", {
      className: "poster",
      title: "Play",
      onclick: () => this._play(),
    });
    const els = {
      video,
      poster,
      posterImg: el("img", { alt: "" }),
      message: el("div", { className: "message" }),
      title: el("div", { className: "title" }),
      meta: el("div", { className: "meta" }),
      channels: el("div", { className: "channels" }),
    };
    poster.append(els.posterImg, el("span", { className: "play" }, "▶"));
    root.append(
      el("style", { textContent: STYLES }),
      el(
        "ha-card",
        {},
        el("div", { className: "player" }, video, poster, els.message),
        el("div", { className: "info" }, els.title, els.meta),
        els.channels
      )
    );
    this._els = els;
  }

  _time(iso) {
    return new Date(iso).toLocaleTimeString(this._hass?.locale?.language, {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: this._hass?.config?.time_zone,
    });
  }

  _progress(programme) {
    if (!programme) return 0;
    const start = Date.parse(programme.start);
    const end = Date.parse(programme.end);
    return Math.min(100, Math.max(0, ((Date.now() - start) / (end - start)) * 100));
  }

  _render() {
    if (!this._els) return;
    const { video, poster, posterImg, message, title, meta, channels } = this._els;
    const channel = this._selected;
    const playing = this._playingId !== undefined;

    video.hidden = !playing;
    poster.hidden = playing || !channel;
    posterImg.src = channel?.now?.image ?? channel?.logo ?? "";
    message.textContent = this._error ?? this._playError ?? "";
    message.hidden = !message.textContent;

    title.textContent = channel?.now?.title ?? channel?.title ?? "";
    const parts = [];
    if (channel?.now) {
      parts.push(`${channel.title} · ${this._time(channel.now.start)}–${this._time(channel.now.end)}`);
    }
    if (channel?.next) parts.push(`Next ${this._time(channel.next.start)} ${channel.next.title}`);
    meta.textContent = parts.join("   ·   ");

    channels.replaceChildren(
      ...(this._channels ?? []).map((c) =>
        el(
          "button",
          {
            className: `channel${c.id === this._selectedId ? " selected" : ""}`,
            title: c.now ? `${c.title}: ${c.now.title}` : c.title,
            onclick: () => this._select(c),
          },
          c.logo ? el("img", { src: c.logo, alt: "" }) : null,
          el(
            "div",
            { className: "text" },
            el("div", { className: "name" }, c.title),
            el("div", { className: "now" }, c.now?.title ?? "")
          ),
          el(
            "div",
            { className: "bar" },
            el("div", { style: `width:${this._progress(c.now)}%` })
          )
        )
      )
    );
  }
}

const STYLES = `
  ha-card { overflow: hidden; }
  .player {
    position: relative; aspect-ratio: 16 / 9; background: #000;
  }
  video, .poster { position: absolute; inset: 0; width: 100%; height: 100%; }
  video { background: #000; }
  [hidden] { display: none !important; }
  .poster {
    padding: 0; border: 0; cursor: pointer; background: #000;
  }
  .poster img { width: 100%; height: 100%; object-fit: cover; opacity: 0.7; }
  .play {
    position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
    width: 64px; height: 64px; border-radius: 50%; display: grid; place-items: center;
    background: var(--primary-color); color: var(--text-primary-color, #fff);
    font-size: 28px; padding-left: 4px; box-sizing: border-box;
  }
  .message {
    position: absolute; left: 12px; right: 12px; bottom: 12px; padding: 8px 12px;
    border-radius: 8px; background: rgba(0, 0, 0, 0.75); color: #fff; font-size: 14px;
  }
  .info { padding: 12px 16px 4px; }
  .title {
    font-size: 18px; font-weight: 500; color: var(--primary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .meta { font-size: 13px; color: var(--secondary-text-color); margin-top: 2px; }
  .channels {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 8px; padding: 8px 16px 16px;
  }
  .channel {
    position: relative; display: flex; align-items: center; gap: 10px;
    padding: 8px 10px 12px; border-radius: 12px; cursor: pointer; text-align: left;
    background: var(--secondary-background-color);
    border: 2px solid transparent; color: var(--primary-text-color); font: inherit;
    overflow: hidden;
  }
  .channel.selected { border-color: var(--primary-color); }
  .channel img { width: 36px; height: 36px; border-radius: 6px; flex: none; }
  .text { min-width: 0; }
  .name { font-weight: 500; font-size: 14px; }
  .now {
    font-size: 12px; color: var(--secondary-text-color);
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .bar { position: absolute; left: 0; right: 0; bottom: 0; height: 3px; background: var(--divider-color); }
  .bar > div { height: 100%; background: var(--primary-color); }
`;

if (!customElements.get("dr-tv-card")) {
  customElements.define("dr-tv-card", DrTvCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "dr-tv-card",
    name: "DR TV",
    description: "Watch DR's live channels and see what's on.",
    documentationURL: "https://github.com/ReimerA/ha-dr-stream",
  });
}
