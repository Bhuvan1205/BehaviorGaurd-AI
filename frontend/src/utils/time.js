export function getRelativeTime(timestamp) {
  const ts = new Date(timestamp).getTime();
  const secondsDifference = Math.round((ts - Date.now()) / 1000);

  if (Math.abs(secondsDifference) < 30) {
    return "just now";
  }

  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto', style: 'short' });
  const minutesDifference = Math.round(secondsDifference / 60);
  const hoursDifference = Math.round(minutesDifference / 60);
  const daysDifference = Math.round(hoursDifference / 24);

  if (Math.abs(minutesDifference) < 60) {
    return rtf.format(minutesDifference, 'minute');
  } else if (Math.abs(hoursDifference) < 24) {
    return rtf.format(hoursDifference, 'hour');
  } else {
    return rtf.format(daysDifference, 'day');
  }
}
