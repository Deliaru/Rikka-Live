export class SubtitleBubble {
  constructor(root) {
    this.root = root;
    this.textNode = root.querySelector(".subtitle-bubble__text");
    this.hideTimer = null;
    this.revealTimer = null;
    this.enterTimer = null;
    this.currentText = "";
    this.enabled = true;
    this.reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
  }

  setEnabled(enabled) {
    this.enabled = Boolean(enabled);
    if (!this.enabled) this.hide(0, true);
  }

  show(text, options = {}) {
    const clean = String(text || "").trim();
    if (!this.enabled) return;
    if (!clean || /^[\s，。！？、,.!?]+$/.test(clean)) return;
    if (clean === this.currentText && this.root.dataset.visible === "true") {
      this.setSpeaking(Boolean(options.speaking));
      return;
    }
    window.clearTimeout(this.hideTimer);
    window.clearTimeout(this.revealTimer);
    window.clearTimeout(this.enterTimer);
    this.currentText = clean;
    this.root.hidden = false;
    this.root.dataset.density = this.densityFor(clean);
    this.root.dataset.variant = options.variant || "response";
    this.root.dataset.leaving = "false";
    this.root.dataset.revealing = "false";
    this.root.dataset.entering = "false";
    this.root.dataset.visible = "true";
    this.root.dataset.speaking = options.speaking ? "true" : "false";
    this.root.style.setProperty("--volume-glow", "0");
    this.restartEntrance();
    this.reveal(clean);
    const holdMs = Number(options.holdMs || Math.min(9000, 2400 + clean.length * 90));
    if (options.autoHide !== false) {
      this.hideTimer = window.setTimeout(() => this.hide(), holdMs);
    }
  }

  densityFor(text) {
    if (text.length >= 70) return "compact";
    if (text.length >= 38) return "cozy";
    return "short";
  }

  restartEntrance() {
    if (this.reducedMotion) return;
    this.root.dataset.entering = "false";
    void this.root.offsetWidth;
    this.root.dataset.entering = "true";
    this.enterTimer = window.setTimeout(() => {
      this.root.dataset.entering = "false";
    }, 520);
  }

  reveal(text) {
    this.textNode.textContent = text;
    if (this.reducedMotion || text.length < 8) return;
    this.root.dataset.revealing = "true";
    this.revealTimer = window.setTimeout(() => {
      this.root.dataset.revealing = "false";
    }, Math.min(740, 280 + text.length * 9));
  }

  setSpeaking(isSpeaking) {
    this.root.dataset.speaking = isSpeaking ? "true" : "false";
  }

  setVolume(volume) {
    const normalized = Math.max(0, Math.min(1, Number(volume) || 0));
    this.root.style.setProperty("--volume-glow", String(normalized * 0.75));
  }

  hide(delayMs = 0, immediate = false) {
    window.clearTimeout(this.hideTimer);
    window.clearTimeout(this.revealTimer);
    window.clearTimeout(this.enterTimer);
    this.hideTimer = window.setTimeout(() => {
      this.root.dataset.visible = "false";
      this.root.dataset.speaking = "false";
      this.root.dataset.revealing = "false";
      this.root.dataset.entering = "false";
      this.root.dataset.leaving = "true";
      this.root.style.setProperty("--volume-glow", "0");
      window.setTimeout(() => {
        if (this.root.dataset.visible !== "true") {
          this.root.hidden = true;
          this.textNode.textContent = "";
          this.currentText = "";
          this.root.dataset.leaving = "false";
          this.root.dataset.density = "";
          this.root.dataset.variant = "";
        }
      }, immediate ? 0 : 320);
    }, delayMs);
  }
}

window.RikkaSubtitleBubble = SubtitleBubble;
