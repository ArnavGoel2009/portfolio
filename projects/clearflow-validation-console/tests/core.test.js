const assert=require("assert");const c=require("../core.js");const date=new Date("2026-08-08T08:00:00.000Z");
const one=c.sanitizeTrial({id:"a",toolHead:"Auger",blockage:"wet silt",durationSeconds:"12.5",outcome:"success",jammed:"no",cameraUseful:"yes",notes:"cleared"},date);
assert.strictEqual(one.durationSeconds,12.5);assert.strictEqual(one.jammed,false);assert.strictEqual(one.cameraUseful,true);
assert.throws(()=>c.sanitizeTrial({toolHead:"",blockage:"x",outcome:"success",jammed:"no"}),/Tool head/);
assert.throws(()=>c.sanitizeTrial({toolHead:"Auger",blockage:"x",outcome:"unknown",jammed:"no"}),/outcome/);
const trials=[one,c.sanitizeTrial({id:"b",toolHead:"Auger",blockage:"fibre",durationSeconds:20,outcome:"success",jammed:"yes",cameraUseful:"no"},date),c.sanitizeTrial({id:"c",toolHead:"Hook",blockage:"fibre",durationSeconds:44,outcome:"fail",jammed:"yes"},date),c.sanitizeTrial({id:"demo",toolHead:"Brush",blockage:"DEMO",durationSeconds:1,outcome:"success",jammed:"no",isDemo:true},date)];
const m=c.metrics(trials);assert.strictEqual(m.total,3);assert.strictEqual(m.successRate,2/3);assert.strictEqual(m.jamRate,2/3);assert.strictEqual(m.medianSuccessSeconds,16.25);assert.strictEqual(c.median([1,4,2,3]),2.5);assert.strictEqual(c.median([]),null);
const csv=c.toCsv(trials);assert(csv.includes("toolHead"));assert(csv.includes("wet silt"));assert(csv.includes("demo"));const summary=c.claimSummary(trials);assert(summary.includes("3 real controlled trials"));assert(summary.includes("67% fully cleared"));
console.log("ClearFlow Validation Console core tests passed.");
