// Run directly with: node CalCloud/portal.test.cjs
const assert = require('node:assert/strict');
const {matchesFilters, displayDate, csvValue} = require('./static/CalCloud/portal.js');
const row = {barcode:'00123', active:true, status:'Due', brand:'FLUKE', due_date:'2026-09-25', clean_date:null, barcodes:['00123','00456']};
assert(matchesFilters(row, {barcode:'001', active:'yes', brand:'fluke', due_date_min:'2026-09-25', due_date_max:'2026-09-25'}));
assert(!matchesFilters(row, {active:'no'}));
assert(!matchesFilters(row, {status:'Overdue'}));
assert(!matchesFilters(row, {clean_date_min:'2026-01-01'}));
assert(!matchesFilters(row, {due_date_max:'2026-09-24'}));
assert(matchesFilters(row, {barcodes:'00456'}));
assert.equal(displayDate('2026-09-25'), '09/25/2026');
assert.equal(displayDate(null), 'N/A');
assert.equal(csvValue('=1+2'), "'=1+2");
assert.equal(csvValue('00123'), '00123');
assert.equal(csvValue(false), 'No');
console.log('CalCloud filter, date, identifier, and CSV checks passed.');
