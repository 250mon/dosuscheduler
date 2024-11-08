export const compareDates = (date1, date2) => {
  date1.setHours(0, 0, 0, 0);
  date2.setHours(0, 0, 0, 0);
  if (date1 > date2) {
    return 1;
  } else if (date1 < date2) {
    return -1;
  } else {
    return 0;
  }
};
