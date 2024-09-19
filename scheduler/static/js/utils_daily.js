// utils.js
const convertStrTime = (timeString) => {
  const time = new Date(`1970-01-01T${timeString}`);
  return time;

  // const [hours, minutes] = timeString.split(":").map(Number);
  // const time = new Date();
  // time.setHours(hours);
  // time.setMinutes(minutes);
  // return time;
};

export const updateDateDisplay = (currentDate, dateDisplay) => {
  const year = currentDate.getFullYear();
  const month = currentDate.getMonth() + 1;
  const day = currentDate.getDate();

  const weekdaysKorean = ["일", "월", "화", "수", "목", "금", "토"];
  const weekdayKorean = weekdaysKorean[currentDate.getDay()];

  dateDisplay.text(`${year} . ${month} . ${day} (${weekdayKorean})`);
  document.title = `Dosu - ${year} / ${month} / ${day} (${weekdayKorean})`;
};

// Format the Date object into "YYYY-MM-DD"
export const formatDate = (date) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0"); // getMonth() returns 0-11, so add 1
  const day = String(date.getDate()).padStart(2, "0");
  const formattedDate = `${year}-${month}-${day}`;
  return formattedDate;
};

export const compareWithToday = (date) => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  date.setHours(0, 0, 0, 0);
  if (date > today) {
    return 1;
  } else if (date < today) {
    return -1;
  } else {
    return 0;
  }
};

// This is a collection of handleAvailableSlotClicks for available slots
export const handlers = {};

// Later in applyScheduleData, the handler_fn will be implemented
export const handleAvailableSlotClick = {
  handler_fn: function (event, timeSlot) {
    console.log("It is a handler function for ", timeSlot);
  },
};

// Because the event handler is supposed to be a single parameter(event)
// function. we create a higher-order function to wrap the event handler
// that has more parameters
export function getSlotClickHandler(timeSlot) {
  let handler = handlers[`${timeSlot.room}-${timeSlot.slot}`];
  if (!handler) {
    handler = function (event) {
      handleAvailableSlotClick.handler_fn(event, timeSlot);
    };
    handlers[`${timeSlot.room}-${timeSlot.slot}`] = handler;
  }
  return handler;
}

function* timeSlotGenerator(hs) {
  let time = hs.startHour;
  let slotIndex = 0;
  let divider = false;

  const morningEnd = hs.lunchStartHour || convertStrTime("13:00");
  const afternoonEnd = hs.overtimeHour || convertStrTime("18:00");

  while (time < hs.endHour) {
    // check if a divider is needed
    const prevTime = new Date(time - hs.duration);
    if (
      (prevTime < morningEnd && time >= morningEnd) ||
      (prevTime < afternoonEnd && time >= afternoonEnd)
    ) {
      divider = true;
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

    const formattedTime =
      time.getHours().toString().padStart(2, "0") +
      ":" +
      time.getMinutes().toString().padStart(2, "0");

    yield {
      slotIndex,
      hour: time.getHours(),
      timeDisplay: formattedTime,
      divider,
    };

    time.setTime(time.getTime() + hs.duration);
    slotIndex++;
    divider = false;
  }
}

export const generateTable = (
  userPrivilege,
  timeslotConfig,
  currentDate,
  statusFilter,
  getSlotClickHandler,
) => {
  $.each([$("#room1"), $("#room2")], (roomIndex, roomContainer) => {
    roomContainer.empty();

    const headContainer = $("<h3>")
      .addClass("head-container")
      .appendTo(roomContainer);
    headContainer.text(`도 수 ${roomIndex + 1}`);

    let currentHour = null;
    let hourContainer = null;

    const isSaturday = currentDate.getDay() === 6;

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
    const slotGen = timeSlotGenerator(hoursConfig);

    for (let { slotIndex, hour, timeDisplay, divider } of slotGen) {
      if (divider) {
        $("<hr>")
          .css({ height: "5px", backgroundColor: "#ffee58", border: "none" })
          .appendTo(roomContainer);
      }

      if (currentHour !== hour) {
        currentHour = hour;
        hourContainer = $("<div>")
          .addClass("hour-container")
          .appendTo(roomContainer);
      }

      const timeSlotDiv = $("<div>")
        .addClass("time-slot")
        .attr("id", `slot${slotIndex}`)
        .appendTo(hourContainer);

      const room = roomIndex + 1;
      const slot = slotIndex;
      const timeSlot = { date: currentDate, room: room, slot: slot };
      // 1. When the statusFilter is active:
      // only the timeSlotDivs of today and afterwards are available.
      // slotClickHandler will create a dosusess if the slot is not active.
      // 2. Otherwise, a detailDosuSessModal appears, which is added
      // in applyScheduleData.
      if (
        statusFilter === "active" &&
        (userPrivilege > 2 || compareWithToday(currentDate) >= 0)
      ) {
        // In applyScheduleData, "available" will be replaced with "status-active"
        // for occupied slots
        timeSlotDiv.addClass("available");
        const clickHandler = getSlotClickHandler(timeSlot);
        timeSlotDiv.on("click", clickHandler);
      } else if (statusFilter !== "active") {
        timeSlotDiv.addClass("empty");
        timeSlotDiv.on("click", (event) => {
          if ($(event.currentTarget).hasClass("empty")) {
            const toastBody = $(".toast-body");
            const msg = "입력하려면 설정을 Active 상태로 바꿔주세요.";
            toastBody.text(msg);
            const toastBootstrap = bootstrap.Toast.getOrCreateInstance(
              $("#alert-toast"),
            );
            toastBootstrap.show();
          }
        });
      }

      $("<div>").addClass("time-span").text(timeDisplay).appendTo(timeSlotDiv);
      $("<div>").addClass("dosusess-container").appendTo(timeSlotDiv);
    }
  });
};

export const fetchSchedule = async (csrfToken, currentDate) => {
  const data = { date: currentDate };
  data.date = formatDate(data.date);
  return fetch("/dosusess/get_schedule", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrfToken,
    },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => data);
};
