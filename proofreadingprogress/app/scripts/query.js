const base = `${window.location.origin}/${
  document.getElementById("prefix").innerText || ""
}/api/v1`;
const params = new URL(document.location).searchParams;
const auto_rootid = params.get("rootid");
const auto_submit = params.get("submit");
const auto_dataset = params.get("dataset");
const wparams = `location=no,toolbar=no,menubar=no,width=620,left=0,top=0`;

document
  .querySelectorAll("#info")
  .forEach((e) =>
    e.addEventListener("click", (v) => v.stopImmediatePropagation())
  );
// HELPERS
function percent(num) {
  var m = Number((Math.abs(num) * 10000).toPrecision(15));
  return (Math.round(m) * Math.sign(num)) / 100;
}
function clrPopup(popup, data) {
  try {
    popup.app = null;
  } catch {}
}
function partition(items, size) {
  var p = [];
  for (var i = Math.ceil(items.length / size); i-- > 0; ) {
    p[i] = items.slice(i * size, (i + 1) * size);
  }
  return p;
}
function setPopup(popup, data) {
  try {
    popup.app.$data.headers = data.headers;
    popup.app.$data.response = data.response;
  } catch {
    setTimeout(() => {
      setPopup(popup, data);
    }, 250);
  }
}
function openWindowWithGet(url, data, name = "", params = "") {
  // var usp = new URLSearchParams(data);
  // var popup = window.open(url, name, params);
  var popup = window.open(url, name); //, params);
  clrPopup(popup, data);
  setPopup(popup, data);
}
function openWindowWithPost(url, data) {
  var form = document.createElement("form");
  form.target = "_blank";
  // TODO: modify to work better
  form.method = "POST";
  form.action = url;
  form.style.display = "none";

  for (var key in data) {
    var input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = data[key];
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}
function importCSVCheck(id) {
  return /^ *\d+ *(?:, *\d+ *)*$/gm.test(id) ? id : 0;
}

const app = new Vue({
  el: "#app",
  mounted() {
    if (auto_submit) this.apiRequest();
  },
  data: {
    // INPUT
    query: {root_id: auto_rootid || "", filtered: true, lineage: true},
    excelcsv: false,
    dataset: auto_dataset || default_dataset,
    str_multiquery: "",
    // OUTPUT
    error: "",
    warn: "",
    failedIDs: [],
    failedIDString: "",
    response: [],
    headers: [],
    csv: "",
    userCSV: "",
    ex_csv: "",
    userList: {},
    userHeaders: [],
    // IMPORT
    colChoices: [],
    keyindex: 0,
    importedCSVName: "",
    importedCSVFile: [],
    importOverride: 0,
    idToRowMap: {},
    // ETC
    status: "Submit",
    loading: false,
  },
  computed: {
    isReady: function () {
      return (
        ((this.query.root_id.length && !isNaN(parseInt(this.query.root_id))) ||
          this.str_multiquery.length) &&
        this.rootsIDTest() &&
        !this.loading
      );
    },
    validRoots: function () {
      const valid = this.rootsIDTest();
      return {
        "form-error": !valid,
        valid,
      };
    },
    rootCount: function () {
      return !this.str_multiquery.length
        ? 0
        : this.str_multiquery.split(/[ ,]+/).length;
    },
  },
  methods: {
    rootsIDTest: function () {
      return (
        /^ *\d+ *(?:, *\d+ *)*$/gm.test(this.str_multiquery) ||
        /^ *\d+ *(?: +\d+ *)*$/gm.test(this.str_multiquery) ||
        !this.str_multiquery.length
      );
    },
    apiRequest: async function () {
      // Disable button, activate spinner
      this.loading = true;
      this.status = "Loading...";
      const request = new URL(`${base}/qry/`);
      if (!this.query.root_id.length) {
        // request.searchParams.set('queries', this.str_multiquery);
      } else {
        request.searchParams.set("query", this.query.root_id);
      }
      request.searchParams.set("dataset", this.dataset);
      request.searchParams.set("filtered", this.query.filtered);
      request.searchParams.set("lineage", this.query.lineage);

      const responses = [];
      const rawRequests = this.str_multiquery.split(/[ ,\n]+/);
      const requests = Array.from(new Set(rawRequests));
      const dupCount = rawRequests.length - requests.length;
      this.warn = dupCount ? `${dupCount} duplicates removed.` : "";
      const batches = partition(requests, 100);
      let failed = 0;
      for (const reqSet of batches) {
        try {
          // Reset to zero
          this.failedIDs = [];
          this.failedIDString = "";
          this.error = ``;
          responses.push(
            await fetch(request, {
              method: "POST",
              headers: {
                Accept: "application/json",
                "Content-Type": "application/json",
              },
              body: JSON.stringify({queries: reqSet.join(",")}),
            })
          );
        } catch (e) {
          this.failedIDs = [...this.failedIDs, ...reqSet];
          this.failedIDString = this.failedIDs.join(", ");
          this.error = `Could not communicate with server, please retry the following IDs:\n`;
        }
      }
      console.log(responses);
      try {
        const resArray = await Promise.all(
          responses.map(async (r) => await r.json())
        );
        const jsonArray = resArray.map((d) => d.json).flat();
        const errorArray = resArray.map((d) => d.error).flat();
        if (this.error == "" && errorArray.length) {
          this.failedIDs = errorArray;
          this.failedIDString = errorArray.join(", ");
          this.error = `The following ids could not be processed.`;
        }
        console.log(
          `${requests.length} requests, ${jsonArray.length} responses`
        );
        await this.processData(jsonArray);
        this.status = "Submit";
        this.loading = false;
      } catch (e) {
        this.loading = false;
        this.status = "Submit";
        this.warn = e;
        throw e;
      }
    },
    processData: function (rawData) {
      const singleRow = rawData[0];
      if (!this.str_multiquery.length && rawData[0]) {
        if (singleRow.edits.length) {
          this.headers = Object.keys(singleRow.edits[0]);
          singleRow.edits.forEach((row) => {
            if (row.timestamp) {
              row.timestamp = new Date(row.timestamp).toUTCString();
            }
          });
          this.response = singleRow.edits;
          const csv = [
            this.headers,
            ...this.response.map((e) => Object.values(e)),
          ];
          this.csv = Papa.unparse(csv);
        } else {
          this.warn = `Root ID ${this.query.root_id} has no edits`;
        }
      } else if (this.str_multiquery.length) {
        this.queryProcess(rawData);
      }
    },
    queryProcess: function (data) {
      /* In lieu of aggreation on server/batching of request
       * Assume user_id always present*
      Array of SegmentIdResponse Arrays => UserIDMap where each UserID has
      array of edits per segmentID
       */
      const userIdsHash = {};
      const segmentList = [];
      data.forEach((seg, i) => {
        const id = seg.key;
        seg.edits.forEach((f) => {
          if (!userIdsHash[f.user_id]) {
            userIdsHash[f.user_id] = {
              user_id: f.user_id,
              user_name: f.user_name,
            };
          }
          if (!userIdsHash[f.user_id][id]) {
            userIdsHash[f.user_id][id] = {
              number_of_edits: 1,
            };
          } else {
            userIdsHash[f.user_id][id].number_of_edits++;
          }
        });
        const segMapRow = [
          ["segment_ID", id],
          ["total_edits", seg.edits.length],
          //['published', seg.published],
        ];
        if (this.query.lineage) {
          // segMapRow.push(['published_ancestor', seg.lineage ?? 'N/A']);
        }
        segmentList.push(new Map(segMapRow));
      });
      this.generateResponse(segmentList, userIdsHash);
    },
    generateResponse: function (segments, uids) {
      this.userHeaders = [
        "user_name",
        "user_id",
        "total_edits",
        "contributed>10%",
      ];
      let userList = {};
      this.response = segments.map((seg) => {
        let headers = Array.from(seg.keys());
        let row = Array.from(seg.values());
        seg.set("contributor", []);

        let segId = seg.get("segment_ID");
        let isPublished = seg.get("published");
        // there may be a better way to sort (requires filtering)
        let contributor = Object.keys(uids)
          .filter((a) => uids[a][segId])
          .sort(
            (a, b) =>
              uids[b][segId].number_of_edits - uids[a][segId].number_of_edits
          );

        contributor.forEach((uid) => {
          let user = uids[uid];
          let contributed = user[segId];
          let edits =
            contributed && !isPublished ? contributed.number_of_edits : 0;

          let percentEdits = percent(edits / seg.get("total_edits"));
          let contributor = new Map([
            ["user_name", user.user_name],
            ["user_id", uid],
            ["number_of_edits", edits],
            ["percent_of_total", percentEdits],
          ]);
          headers = headers.concat(Array.from(contributor.keys()));
          row = row.concat(Array.from(contributor.values()));
          seg.get("contributor").push(contributor);
          if (!userList[uid]) {
            userList[uid] = {
              user_name: user.user_name,
              user_id: uid,
              total_edits: 0,
              contributed_at_least_10Percent: 0,
            };
          }
          userList[uid].total_edits += edits;
          userList[uid].contributed_at_least_10Percent +=
            percentEdits >= 10 ? 1 : 0;
        });
        if (this.headers.length < headers.length) {
          this.headers = headers;
        }
        return row;
      });
      this.userList = Array.from(Object.values(userList));
      const csv = [this.headers, ...this.response];
      this.csv = Papa.unparse(csv);
      this.userCSV = Papa.unparse(this.userList);

      const ex_res = this.response.map((row) => {
        var newRow = [...row];
        newRow[0] = `'${newRow[0]}`;
        return newRow;
      });
      const ex_csv = [this.headers, ...ex_res];
      this.ex_csv = Papa.unparse(ex_csv);
    },
    exportCSV: function () {
      rawExport("edits.csv", this.excelcsv ? this.ex_csv : this.csv);
    },
    exportSingleCSV: function () {
      rawExport("changelog.csv", this.csv);
    },
    viewResults: function () {
      let headers = this.headers;
      let response = this.response;
      openWindowWithGet(
        new URL(`${base}/table`),
        {headers, response, select: true},
        `Edits Table`,
        wparams
      );
    },
    mergeCSV: function () {
      const filename = `${this.importedCSVName.name}_merged.csv`;
      const mergedCSV = [...this.importedCSVFile];
      Papa.parse(this.csv, {
        complete: (results) => {
          results.data.map((row, i) => {
            // const key = importCSVCheck(this.idToRowMap[row[0].slice(1)]);
            const key = i ? this.idToRowMap[row[0]] : 0;
            // if (!i) return;
            // const key = this.idToRowMap[row[0]];
            const firsthalf = mergedCSV[key].slice(0, this.keyindex);
            const secondhalf =
              this.keyindex < mergedCSV[key].length - 1
                ? mergedCSV[key].slice(this.keyindex + 1)
                : [];
            mergedCSV[key] = [...firsthalf, ...secondhalf, ...row];
          });

          const blob = new Blob([Papa.unparse(mergedCSV)], {
            type: "text/csv;charset=utf-8;",
          });
          const link = document.createElement("a");
          const url = URL.createObjectURL(blob);
          link.setAttribute("href", url);
          link.setAttribute("download", filename);
          link.click();
        },
      });
    },
    exportUserCSV: function () {
      rawExport("useredits.csv", this.userCSV);
    },
    viewUsers: function () {
      let headers = this.userHeaders;
      let response = this.userList.map((r) => Object.values(r));
      openWindowWithGet(
        new URL(`${base}/table`),
        {headers, response},
        `User Table`,
        wparams
      );
    },
    importCSV: function (e) {
      Papa.parse(e.target.files[0], {
        // quoteChar: `'`,
        // escapeChar: `\\`,
        skipEmptyLines: true,
        complete: (results) => {
          this.importedCSVName = e.target.files[0];
          this.importedCSVFile = results.data;

          if (!results.data.length) {
            this.warn = `${this.importedCSVName} is empty!`;
          } else if (
            results.data.length > 1 &&
            results.data[0].length != results.data[1].length
          ) {
            this.warn = `Header Row and Row 1 have different amount of columns! Unable to import columns correctly.
            Please ensure that the imported CSV is valid. Every row must have the same amount of commas.`;
          }

          this.colChoices = results.data[0];
        },
      });
    },
    chooseCSV: function () {
      document.getElementById("import").click();
    },
    importCol: function (index) {
      const multiquery = [];
      let badRows = 0;
      this.importedCSVFile.forEach((e, i) => {
        try {
          this.keyindex = index;
          let rid = e[index];
          // Remove Leading ' on import
          if (rid[0] == "'" && rid.length > 1) rid = rid.slice(1);
          // Remove invalid root_ids
          rid = importCSVCheck(rid);
          if (rid) {
            this.idToRowMap[rid] = i;
            multiquery.push(rid);
          }
        } catch {
          badRows++;
          this.warn = `${badRows} rows could not be imported. Index out of bounds.`;
        }
      });

      this.str_multiquery = !multiquery.length ? "" : multiquery.join(", ");
    },
    overrideImport: function () {
      this.importCol(Number(this.importOverride));
    },
  },
});

$(function () {
  $('[data-toggle="tooltip"]').tooltip();
});

function rawExport(name, csv) {
  const filename = name;
  const blob = new Blob([csv], {type: "text/csv;charset=utf-8;"});
  const link = document.createElement("a");
  const url = URL.createObjectURL(blob);
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.click();
}
