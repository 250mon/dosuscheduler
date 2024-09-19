import {
  updateDateDisplay,
  formatDate,
  compareWithToday,
  generateTable,
  fetchSchedule,
  handleAvailableSlotClick,
  getSlotClickHandler,
} from "./utils_daily.js";

const realSlotClickHandler = (event, timeSlot) => {
  const selectedTimeSlot = $(".dosusess-list-container").find(".selected");
  if (selectedTimeSlot.length) {
    selectedTimeSlot.removeClass("selected");
  }

  if ($(event.currentTarget).hasClass("available")) {
    $(event.currentTarget).addClass("selected");

    // Format the Date object into "YYYY-MM-DD"
    const formattedDate = formatDate(timeSlot.date);
    const room = timeSlot["room"];
    const slot = timeSlot["slot"];
    $("#update-room").val(room);
    $("#update-date").val(`${formattedDate}`);
    $("#update-slot").val(slot);
  }
};

const applyScheduleData = (schedule) => {
  handleAvailableSlotClick.handler_fn = realSlotClickHandler;
  $.each(schedule, (index, dosusessEntry) => {
    const { date, room, slot, slot_quantity, patient_name, status } =
      dosusessEntry;

    const sess_date = new Date(date);
    const year = sess_date.getFullYear();
    const month = sess_date.getMonth() + 1;
    const day = sess_date.getDate();
    const timeSlot = { date: sess_date, room: room, slot: slot };

    const roomContainer = room === 1 ? $("#room1") : $("#room2");
    // take slot_quantity
    let timeSlotDiv = roomContainer.find(`#slot${slot}`);
    const timeSlots = [timeSlot];
    for (let i = 1; i < slot_quantity; i++) {
      const additionalTSDiv = roomContainer.find(`#slot${slot + i}`);
      timeSlotDiv = timeSlotDiv.add(additionalTSDiv);
      const additionalTS = { date: sess_date, room: room, slot: slot + i };
      timeSlots.push(additionalTS);
    }

    const dosusessContainer = timeSlotDiv.find(".dosusess-container");

    $("<div>")
      .text(patient_name || "")
      .addClass("patient-name-display")
      .appendTo(dosusessContainer);

    // Apply the color based on the status
    switch (status) {
      case "active":
        timeSlotDiv.removeClass("available").addClass("status-active");
        for (let ts in timeSlots) {
          const clickHandler = getSlotClickHandler(timeSlots[ts]);
          timeSlotDiv.off("click", clickHandler);
        }
        break;
      default:
        timeSlotDiv.addClass("status-default");
        break;
    }
  });
};

$(document).ready(function () {
  const dosusessListContainer = $(".dosusess-list-container");
  const dateDisplay = $("#date-display");
  const prevDateButton = $("#prev-day");
  const nextDateButton = $("#next-day");
  const csrfToken = $('meta[name="csrf_token"]').attr("content");

  const userPrivilege = dosusessListContainer.data("user_privilege");
  // statusFilter should be always 'active' to update the schedule
  const statusFilter = dosusessListContainer.data("status_filter");
  let currentDate = new Date(
    parseInt(dosusessListContainer.data("year"), 10),
    parseInt(dosusessListContainer.data("month"), 10) - 1,
    parseInt(dosusessListContainer.data("day"), 10),
  );

  const changeDate = async (increment) => {
    currentDate.setDate(currentDate.getDate() + increment);
    if (currentDate.getDay() === 0) {
      // To skip Sundays
      currentDate.setDate(currentDate.getDate() + increment);
    }

    updateDateDisplay(currentDate, dateDisplay);

    const data = await fetchSchedule(csrfToken, currentDate);
    const timeslotConfig = data.timeslotConfig;
    const dSchedule = data.schedule;
    generateTable(
      userPrivilege,
      timeslotConfig,
      currentDate,
      statusFilter,
      getSlotClickHandler,
    );
    applyScheduleData(dSchedule);
  };
  prevDateButton.on("click", () => {
    if (compareWithToday(currentDate) > 0) {
      changeDate(-1);
    }
  });
  nextDateButton.on("click", () => changeDate(1));

  try {
    changeDate(0);
  } catch (error) {
    console.error("Error loading schedule:", error);
  }
});
