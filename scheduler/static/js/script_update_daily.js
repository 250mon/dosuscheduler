import {
  updateDateDisplay,
  formatDate,
  compareWithToday,
  generateTable,
  fetchSchedule,
  handleAvailableSlotClick,
  getSlotClickHandler,
} from "./utils_daily.js";
import { createDosutypeSelect } from "./script_create.js";

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
    $("#updateRoom").val(room);
    $("#updateDate").val(`${formattedDate}`);
    $("#updateSlot").val(slot);
  }
};

const applyScheduleData = (lastSlotIndex, schedule) => {
  handleAvailableSlotClick.handler_fn = realSlotClickHandler;
  const update_dosusess_id = $("#infoId").data("dosusess-id");
  $.each(schedule, (index, dosusessEntry) => {
    const { id, date, room, slot, slot_quantity, mrn, patient_name, status } =
      dosusessEntry;

    const sess_date = new Date(date);
    const timeSlot = { date: sess_date, room: room, slot: slot };

    const roomContainer = room === 1 ? $("#room1") : $("#room2");
    // take slot_quantity
    let timeSlotDiv = roomContainer.find(`#slot${slot}`);
    const timeSlots = [timeSlot];
    // if the dosusessEntry is the dosusess to update,
    // its additional time slots shoud be available slots
    if (id !== update_dosusess_id) {
      for (let i = 1; i < slot_quantity; i++) {
        if (slot + i > lastSlotIndex) {
          break;
        }
        const additionalTSDiv = roomContainer.find(`#slot${slot + i}`);
        timeSlotDiv = timeSlotDiv.add(additionalTSDiv);
        const additionalTS = { date: sess_date, room: room, slot: slot + i };
        timeSlots.push(additionalTS);
      }
    }

    const dosusessContainer = timeSlotDiv.find(".dosusess-container");

    $("<div>")
      .text(patient_name || "")
      .addClass("patient-name-display")
      .appendTo(dosusessContainer);

    // make the timeslots assigned to the schedule unavailable
    switch (status) {
      case "active":
        timeSlotDiv.removeClass("available");
        if (mrn === 0) {
          // block time slot
          timeSlotDiv.addClass("disabled");
        } else {
          timeSlotDiv.addClass("status-active");
        }
        for (let ts in timeSlots) {
          const clickHandler = getSlotClickHandler(timeSlots[ts]);
          timeSlotDiv.off("click", clickHandler);
        }
        break;
      default: // not reach here
        timeSlotDiv.addClass("status-default");
        break;
    }
  });
};

$(document).ready(function () {
  // display a dosutype select options
  const dosutypeSelect = document.getElementById("dosutypeSelect");
  const patientId = dosutypeSelect.getAttribute("data-patient-id");
  const dosutypeId = dosutypeSelect.getAttribute("data-dosutype-id");
  createDosutypeSelect(dosutypeSelect, patientId, dosutypeId);

  // display a daily list for changing schedule
  const dosusessListContainer = $(".dosusess-list-container");
  const dateDisplay = $("#dateDisplay");
  const prevDateButton = $("#prevDay");
  const nextDateButton = $("#nextDay");
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
    const lastSlotIndex = generateTable(
      userPrivilege,
      timeslotConfig,
      currentDate,
      statusFilter,
      getSlotClickHandler,
    );
    applyScheduleData(lastSlotIndex, dSchedule);
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
