const updateMonthDisplay = (currentDate) => {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;
  $(".month-display").text(`${year} . ${month}`);
  document.title = `Dosu - ${year} / ${month}`;
};

const createToolTip = (timeSegment) => {
  const tooltipText = $("<span>").addClass("tooltiptext");
  timeSegment.on("mouseover", function () {
    tooltipText.text(timeSegment.data("patient_name"));
  });
  return tooltipText;
};

const setSegmentActive = (day, lastSlotIndex, daySchedule) => {
  daySchedule.forEach((dosusess) => {
    const { patient_name, mrn, slot_quantity, room, slot, status } = dosusess;
    var timeSegments = $();
    for (let i = 0; i < slot_quantity; i++) {
      if (slot + i > lastSlotIndex) {
        break;
      }
      const segmentDiv = $(`#room${room}-day${day}-segment-${slot + i}`);
      timeSegments = timeSegments.add(segmentDiv);
    }

    if (timeSegments.length) {
      timeSegments.each(function () {
        $(this)
          .data({ patient_name, status })
          .removeClass("inactive disabled")
          .addClass("time-segment");
        if (mrn === 0) {
          $(this)
            .addClass("blocked")
            .append(createToolTip($(this)));
        } else {
          $(this)
            .addClass(
              status === "noshow"
                ? "noshow"
                : status === "canceled"
                  ? "canceled"
                  : "active",
            )
            .append(createToolTip($(this)));
        }
      });

      if (timeSegments.length > 1) {
        const timeSegmentsAfterFirst = timeSegments.slice(1);
        timeSegmentsAfterFirst.css("border-left", "none");
      }
    }
  });
};

function* timeSegmentGenerator(hs) {
  let time = hs.startHour;

  let slotIndex = 0;
  let timeBarCreate = true;
  let barSlotCount = 0;

  const morningEnd = hs.lunchStartHour || convertStrTime("13:00");
  const afternoonStart = hs.lunchEndHour || convertStrTime("14:00");
  const afternoonEnd = hs.overtimeHour || convertStrTime("18:00");

  const morningSlotCount = (morningEnd - hs.startHour) / hs.duration;
  const afternoonSlotCount = (hs.overtimeHour - afternoonStart) / hs.duration;
  const overtimeSlotCount = (hs.endHour - hs.overtimeHour) / hs.duration;
  const maxSlotsInBar = Math.max(
    morningSlotCount,
    afternoonSlotCount,
    overtimeSlotCount,
  );

  while (time < hs.endHour || barSlotCount < maxSlotsInBar) {
    // check if a new time bar is needed
    const prevTime = time - hs.duration;
    if (
      (prevTime < morningEnd && time >= morningEnd) ||
      (prevTime < afternoonEnd && time >= afternoonEnd)
    ) {
      timeBarCreate = true;
      // place dummy slots in order to align the bar lengths
      while (barSlotCount < maxSlotsInBar) {
        yield { timeBarCreate: false, slotIndex: -1, hour: -1 };
        barSlotCount++;
      }
      barSlotCount = 0;
    }

    // if it is lunch hours, skip it
    if (
      hs.lunchStartHour &&
      time >= hs.lunchStartHour &&
      time < hs.lunchEndHour
    ) {
      time = hs.lunchEndHour;
      continue;
    }

    yield { timeBarCreate, slotIndex, hour: time.getHours() };

    timeBarCreate = false;
    time.setTime(time.getTime() + hs.duration);
    slotIndex++;
    barSlotCount++;
  }
}

const createDayDetail = (timeslotConfig, isSaturday, day) => {
  const dayContainer = $("<div>").addClass("day-container");
  let lastSlotIndex = 0;

  ["room1", "room2"].forEach((roomClass) => {
    const roomContainer = $("<div>")
      .addClass("room-container")
      .addClass(roomClass);

    let hoursConfig = {};
    hoursConfig.duration = timeslotConfig.duration * 60 * 1000;
    if (isSaturday) {
      hoursConfig.startHour = convertStrTime(timeslotConfig.sd_start_hour);
      hoursConfig.endHour = convertStrTime(timeslotConfig.sd_end_hour);
      hoursConfig.overtimeHour = convertStrTime(
        timeslotConfig.sd_overtime_hour,
      );
    } else {
      hoursConfig.startHour = convertStrTime(timeslotConfig.wd_start_hour);
      hoursConfig.endHour = convertStrTime(timeslotConfig.wd_end_hour);
      hoursConfig.lunchStartHour = convertStrTime(
        timeslotConfig.wd_lunch_start_hour,
      );
      hoursConfig.lunchEndHour = convertStrTime(
        timeslotConfig.wd_lunch_end_hour,
      );
      hoursConfig.overtimeHour = convertStrTime(
        timeslotConfig.wd_overtime_hour,
      );
    }
    const segGen = timeSegmentGenerator(hoursConfig);
    const overtimeHour = hoursConfig.overtimeHour.getHours();

    let timeBar;
    for (let { timeBarCreate, slotIndex, hour } of segGen) {
      if (timeBarCreate) {
        // new time-bar container
        timeBar = $("<div>").addClass("time-bar");
        roomContainer.append(timeBar);
      }

      const timeSegment = $("<div>").attr(
        "id",
        `${roomClass}-day${day}-segment-${slotIndex}`,
      );

      // dummy time segments for aligning the bar lengths
      if (hour === -1) {
        timeSegment.addClass("time-segment disabled");
      } else {
        timeSegment.addClass(
          `time-segment ${hour >= overtimeHour ? "overtime disabled" : "inactive"}`,
        );
      }
      timeBar.append(timeSegment);
      lastSlotIndex = slotIndex;
    }
    dayContainer.append(roomContainer);
  });
  return { dayContainer, lastSlotIndex };
};

const generateCalendar = (
  year,
  month,
  mSchedule,
  timeslotConfig,
  newPatientCount,
) => {
  // update new patient count
  const newPtCountDiv = $("#newPatientCount");
  newPtCountDiv.empty();
  $.each(newPatientCount, (index, npcEntry) => {
    const { worker_name, count, patient_names } = npcEntry;
    console.log(typeof patient_names, patient_names);
    $("<div>")
      .attr("type", "button")
      .addClass("btn")
      .attr("data-bs-toggle", "popover")
      .attr("data-bs-title", worker_name)
      .attr("data-bs-content", patient_names.join(", "))
      .text(`${worker_name}: ${count}`)
      .appendTo(newPtCountDiv);
  });

  // initialize popover using jQuery with options
  $('[data-bs-toggle="popover"]').popover({
    trigger: "hover",
    placement: "down",
    html: true,
    delay: { show: 100, hide: 100 },
    container: "body",
  });

  // update calendar body
  const calendarBody = $(".calendar-body");
  calendarBody.empty();
  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();

  for (let i = 0; i < firstDay; i++) {
    calendarBody.append($("<div>").addClass("day-cell"));
  }

  for (let day = 1; day <= daysInMonth; day++) {
    let lastTimeSlotIndex = 0;
    const dayCell = $("<div>")
      .addClass("day-cell")
      .on(
        "click",
        () =>
          (window.location.href = `/dosusess/daily/${year}/${month}/${day}`),
      );

    dayCell.append($("<div>").text(day).addClass("day-number"));

    const dayOfWeek = (firstDay + day - 1) % 7;
    if (dayOfWeek !== 0) {
      // Skip Sundays
      // dayCell.append(createDayDetail(timeslotConfig, dayOfWeek === 6, day));
      const { dayContainer, lastSlotIndex } = createDayDetail(
        timeslotConfig,
        dayOfWeek === 6,
        day,
      );
      dayCell.append(dayContainer);
      lastTimeSlotIndex = lastSlotIndex;
    }
    calendarBody.append(dayCell);
    if (mSchedule[day]) {
      setSegmentActive(day, lastTimeSlotIndex, mSchedule[day]);
    }
  }
};

const fetchSchedule = async (year, month) => {
  const csrfToken = $('meta[name="csrf_token"]').attr("content");
  fetch("/dosusess/get_schedule", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify({ year: year.toString(), month: month.toString() }),
  })
    .then((response) => response.json())
    .then((data) => {
      const mSchedule = data.schedule;
      const timeslotConfig = data.timeslotConfig;
      const newPatientCount = data.newPatientCount;
      generateCalendar(year, month, mSchedule, timeslotConfig, newPatientCount);
    });
};

// currentDate is passed by reference value
const changeDate = (currentDate, increment, unit) => {
  if (unit === "month") {
    currentDate.setMonth(currentDate.getMonth() + increment);
  } else if (unit === "year") {
    currentDate.setFullYear(currentDate.getFullYear() + increment);
  }
  updateMonthDisplay(currentDate);
  fetchSchedule(currentDate.getFullYear(), currentDate.getMonth() + 1);
};

const convertStrTime = (timeString) => {
  const time = new Date(`1970-01-01T${timeString}`);
  return time;
};

$(document).ready(function () {
  const prevYearButton = $("#prevYear");
  const prevMonthButton = $("#prevMonth");
  const nextYearButton = $("#nextYear");
  const nextMonthButton = $("#nextMonth");
  const calendarContainer = $(".calendar-container");

  let currentDate = new Date(
    parseInt(calendarContainer.attr("data-year"), 10),
    parseInt(calendarContainer.attr("data-month"), 10) - 1,
    1,
  );
  prevYearButton.on("click", () => changeDate(currentDate, -1, "year"));
  nextYearButton.on("click", () => changeDate(currentDate, 1, "year"));
  prevMonthButton.on("click", () => changeDate(currentDate, -1, "month"));
  nextMonthButton.on("click", () => changeDate(currentDate, 1, "month"));

  updateMonthDisplay(currentDate);
  fetchSchedule(currentDate.getFullYear(), currentDate.getMonth() + 1);
});
