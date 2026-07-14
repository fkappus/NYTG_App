// Bermuda Triangle 🍪 — streak widget for Scriptable
// Small widget: your streaks. Medium widget: everyone's.
// Set your name in the widget's "Parameter" field (Finn / Stella / Peter).

const DATA_URL =
  "https://raw.githubusercontent.com/fkappus/NYTG_App/main/streaks.json";
const DASHBOARD_URL = "https://nytgapp-uzjziac7wjm7ieje5gsjn4.streamlit.app/";
const MY_NAME = (args.widgetParameter || "Finn").trim();

const BG = new Color("#0A0A0B");
const GREEN = new Color("#3DFF6E");
const YELLOW = new Color("#FFE23B");
const BLUE = new Color("#4DA6FF");
const PURPLE = new Color("#D96BFF");
const WHITE = new Color("#FFFFFF");
const MUTED = new Color("#8A8A8E");
const CARDBORDER = new Color("#2A2A2C");

const serif = (size, bold) =>
  new Font(bold ? "TimesNewRomanPS-BoldMT" : "TimesNewRomanPSMT", size);

async function loadData() {
  try {
    const req = new Request(DATA_URL + "?t=" + Date.now());
    return await req.loadJSON();
  } catch (e) {
    return null;
  }
}

function tileRow(stack, size) {
  const row = stack.addStack();
  row.spacing = 3;
  for (const c of [YELLOW, GREEN, BLUE, PURPLE]) {
    const t = row.addStack();
    t.size = new Size(size, size);
    t.backgroundColor = c;
    t.cornerRadius = 2;
  }
}

function streakLine(stack, player, fontSize) {
  const line = stack.addStack();
  line.centerAlignContent();
  line.spacing = 6;
  const w = line.addText("W " + player.wordle.current);
  w.font = serif(fontSize, true);
  w.textColor = GREEN;
  const c = line.addText("C " + player.connections.current);
  c.font = serif(fontSize, true);
  c.textColor = PURPLE;
}

function buildSmall(widget, data) {
  const me = data.players.find(
    (p) => p.name.toLowerCase() === MY_NAME.toLowerCase());
  tileRow(widget, 9);
  widget.addSpacer();
  if (!me) {
    const t = widget.addText("Unknown player: " + MY_NAME);
    t.font = serif(14, false);
    t.textColor = WHITE;
    return;
  }
  const wRow = widget.addStack();
  wRow.bottomAlignContent();
  wRow.spacing = 5;
  const wNum = wRow.addText(String(me.wordle.current));
  wNum.font = serif(30, true);
  wNum.textColor = GREEN;
  const wLab = wRow.addText("Wordle");
  wLab.font = serif(12, false);
  wLab.textColor = GREEN;

  const cRow = widget.addStack();
  cRow.bottomAlignContent();
  cRow.spacing = 5;
  const cNum = cRow.addText(String(me.connections.current));
  cNum.font = serif(30, true);
  cNum.textColor = PURPLE;
  const cLab = cRow.addText("Connections");
  cLab.font = serif(12, false);
  cLab.textColor = PURPLE;

  widget.addSpacer();
  const name = widget.addText(me.name);
  name.font = serif(13, false);
  name.textColor = WHITE;
  const best = widget.addText(
    "best: W " + me.wordle.longest + " · C " + me.connections.longest);
  best.font = serif(11, false);
  best.textColor = MUTED;
}

function buildMedium(widget, data) {
  const head = widget.addStack();
  head.centerAlignContent();
  const title = head.addText("Bermuda Triangle 🍪");
  title.font = serif(14, false);
  title.textColor = WHITE;
  head.addSpacer();
  const date = head.addText(data.data_through.slice(5));
  date.font = serif(11, false);
  date.textColor = MUTED;

  widget.addSpacer();
  const row = widget.addStack();
  row.spacing = 8;
  for (const p of data.players) {
    const mine = p.name.toLowerCase() === MY_NAME.toLowerCase();
    const card = row.addStack();
    card.layoutVertically();
    card.setPadding(7, 9, 7, 9);
    card.cornerRadius = 11;
    card.borderWidth = 1;
    card.borderColor = mine ? GREEN : CARDBORDER;
    const name = card.addText(p.name);
    name.font = serif(13, false);
    name.textColor = WHITE;
    name.centerAlignText();
    card.addSpacer(3);
    streakLine(card, p, 15);
    card.addSpacer(3);
    const best = card.addText(
      "best " + p.wordle.longest + "·" + p.connections.longest);
    best.font = serif(10.5, false);
    best.textColor = MUTED;
  }
  widget.addSpacer();
  const foot = widget.addText("current day streaks");
  foot.font = serif(11, false);
  foot.textColor = MUTED;
}

const widget = new ListWidget();
widget.backgroundColor = BG;
widget.url = DASHBOARD_URL;
widget.refreshAfterDate = new Date(Date.now() + 60 * 60 * 1000);

const data = await loadData();
if (!data) {
  const t = widget.addText("Couldn't load streaks");
  t.font = serif(14, false);
  t.textColor = MUTED;
} else if (config.widgetFamily === "medium") {
  buildMedium(widget, data);
} else {
  buildSmall(widget, data);
}

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentMedium();
}
Script.complete();
