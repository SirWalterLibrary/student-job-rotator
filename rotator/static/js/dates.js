// Browser-side date formatting. ISO strings are "YYYY-MM-DD" everywhere.
// "Today" itself always comes from the server (/api/config).
//
// ISO dates are parsed with Date.UTC, never new Date("YYYY-MM-DD"),
// which the browser interprets as UTC midnight and can shift the day.

const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const MONTHS_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** Split an ISO date into { y, m, d } numbers. */
function parts(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return { y, m, d };
}

/** A Date at noon UTC on the given ISO date (avoids Hijri off-by-one). */
function utcDate(iso) {
  const { y, m, d } = parts(iso);
  return new Date(Date.UTC(y, m - 1, d, 12));
}

/** "Saturday" for "2026-11-07". */
export function weekdayName(iso) {
  return WEEKDAYS[(utcDate(iso).getUTCDay() + 6) % 7];
}

/** "November" for "2026-11-07". */
export function monthName(iso) {
  return MONTHS[parts(iso).m - 1];
}

/** "Saturday, November 7, 2026". */
export function longDate(iso) {
  const { y, m, d } = parts(iso);
  return `${weekdayName(iso)}, ${MONTHS[m - 1]} ${d}, ${y}`;
}

/** "Nov 7" (no year). */
export function shortDate(iso) {
  const { m, d } = parts(iso);
  return `${MONTHS_SHORT[m - 1]} ${d}`;
}

let hijriFmt = null;
/** Approximate Hijri date via Umm al-Qura (e.g. "22 Jumada al-Thani 1448 AH"). */
export function hijriDate(iso) {
  if (!hijriFmt) {
    try {
      hijriFmt = new Intl.DateTimeFormat("en-u-ca-islamic-umalqura-nu-latn", {
        day: "numeric",
        month: "long",
        year: "numeric",
        timeZone: "UTC",
      });
    } catch {
      return ""; // browser without the Umm al-Qura calendar
    }
  }
  return hijriFmt.format(utcDate(iso));
}
