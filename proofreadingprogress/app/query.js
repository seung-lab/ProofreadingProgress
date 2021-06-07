const base = `${window.location.origin}/api/v1`;
const params = (new URL(document.location)).searchParams;
const auto_rootid = params.get('rootid');
function percent(num) {
  var m = Number((Math.abs(num) * 10000).toPrecision(15));
  return (Math.round(m) * Math.sign(num)) / 100;
}

// TODO: CLEANUP
const app = new Vue({
  el: '#app',
  data: {
    query: {root_id: auto_rootid || '', historical: false, filtered: true},
    filters: {

    },
    tag: '',
    multiqueryRaw: '',
    multiquery: [],
    rawResponse: [],
    response: [],
    headers: [],
    colChoices: [],
    csv: '',
    userCSV: '',
    userList: {},
    userHeaders: [],
    importedCSVFile: [],
    numval: [{classes: 'numval', rule: /^[0-9]+$/, disableAdd: true}],
    status: 'Submit',
    loading: false
  },
  computed: {
    isReady: function() {
      return (this.query.root_id.length &&
                  !isNaN(parseInt(this.query.root_id)) ||
              this.multiqueryRaw.length) &&
          !this.loading;
    }
  },
  mounted() {
    this.$nextTick(function() {
      // Code that will run only after the
      // entire view has been rendered
      if (this.isReady) {
        this.apiRequest();
      }
    })
  },
  methods: {
    processMQR: function() {
      const multiquerySplit = this.multiqueryRaw.split(/[ ,]+/);
      this.multiquery =
          multiquerySplit.filter(e => e.length && !isNaN(parseInt(e)))
    },
    apiRequest: async function() {
      // Disable button, activate spinner
      this.loading = true;
      this.status = 'Loading...';
      this.processMQR();

      const request = new URL(`${base}/qry/`);
      if (this.multiquery.length) {
        request.searchParams.set('queries', this.multiquery.join(' '));
      } else {
        request.searchParams.set('query', this.query.root_id);
      }

      request.searchParams.set('root_ids', this.query.historical);
      request.searchParams.set('filtered', this.query.filtered);
      if (this.multiquery.length) {
        request.searchParams.set('agg', 'true');
      }

      try {
        const response = await fetch(request);
        await this.processData(await response.json());
        this.status = 'Submit';
        this.loading = false;
      } catch (e) {
        alert(`Root ID: ${this.query.root_id} is invalid.`);
        this.loading = false;
        this.status = 'Submit';
        throw e;
      }
    },
    processData: function(response) {
      rawData = JSON.parse(response.json);
      if (rawData.length && !this.multiquery.length) {
        this.headers = Object.keys(rawData[0]);
        rawData.forEach(row => {
          if (row.timestamp) {
            row.timestamp = new Date(row.timestamp).toUTCString();
          }
        });
        this.response = rawData;
        this.csv = response.csv.replace(/\[|\]/g, '');
      } else if (this.multiquery.length) {
        this.rawResponse = rawData;
        this.queryProcess();
      }
    },
    queryProcess: function() {
      /* In lieu of aggreation on server/batching of request
       * Assume user_id always present*
      Array of SegmentIdResponse Arrays => UserIDMap where each UserID has array
      of edits per segmentID
       */
      const userIdsHash = {};
      const segmentList = [];
      this.rawResponse.forEach((e, i) => {
        const rawSegment = JSON.parse(e);
        // ASSUME query order is result order
        rawSegment.forEach(f => {
          if (!userIdsHash[f.user_id]) {
            userIdsHash[f.user_id] = {
              user_id: f.user_id,
              user_name: f.user_name
            };
          }
          const id = this.multiquery[i];
          if (!userIdsHash[f.user_id][id]) {
            userIdsHash[f.user_id][id] = {
              number_of_edits: 1,
            };
          } else {
            userIdsHash[f.user_id][id].number_of_edits++;
          }
        });
        segmentList.push(new Map([
          ['segment_ID', this.multiquery[i]],
          ['total_edits', rawSegment.length],
          ['published', ''],
        ]));
      });
      this.generateResponse(segmentList, userIdsHash);
    },
    generateResponse: function(segments, uids) {
      this.userHeaders =
          ['user_name', 'user_id', 'total_edits', 'contributed>10%'];
      let userList = {};
      this.response = segments.map(seg => {
        let headers = Array.from(seg.keys());
        let row = Array.from(seg.values());
        row[0] = `'${row[0]}`;  // Adds ' to front of seg id
        seg.set('contributor', []);

        let segId = seg.get('segment_ID');
        // there may be a better way to sort (requires filtering)
        let contributor = Object.keys(uids)
                              .filter(a => uids[a][segId])
                              .sort(
                                  (a, b) => uids[b][segId].number_of_edits -
                                      uids[a][segId].number_of_edits);

        contributor.forEach(uid => {
          let user = uids[uid];
          let contributed = user[segId];
          let edits = contributed ? contributed.number_of_edits : 0;

          let percentEdits = percent((edits / seg.get('total_edits')));
          let contributor = new Map([
            ['user_name', user.user_name], ['user_id', uid],
            ['number_of_edits', edits], ['percent_of_total', percentEdits]
          ]);
          headers = headers.concat(Array.from(contributor.keys()));
          row = row.concat(Array.from(contributor.values()));
          seg.get('contributor').push(contributor);
          if (!userList[uid]) {
            userList[uid] = {
              user_name: user.user_name,
              user_id: uid,
              total_edits: 0,
              contributed_at_least_10Percent: 0
            };
          }
          userList[uid].total_edits += edits;
          userList[uid].contributed_at_least_10Percent +=
              ((percentEdits >= 10) ? 1 : 0);
        });
        if (this.headers.length < headers.length) {
          this.headers = headers;
        }
        return row;
      });
      const csv = [this.headers, ...this.response];
      this.csv = Papa.unparse(csv);
      this.userList = Array.from(Object.values(userList));
      this.userCSV = Papa.unparse(this.userList);
    },
    exportCSV: function() {
      const filename = 'edits.csv';
      const blob = new Blob([this.csv], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    },
    exportUserCSV: function() {
      const filename = 'useredits.csv';
      const blob = new Blob([this.userCSV], {type: 'text/csv;charset=utf-8;'});
      const link = document.createElement('a');
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.click();
    },
    importCSV: function(e) {
      Papa.parse(e.target.files[0], {
        skipEmptyLines: true,
        complete: (results) => {
          this.importedCSVFile = results.data;
          this.colChoices = results.data[0];
        }
      });
    },
    chooseCSV: function() {
      document.getElementById('import').click();
    },
    importCol: function(index) {
      this.importedCSVFile.forEach((e, i) => {
        if (i) {
          this.multiqueryRaw =
              this.multiqueryRaw.concat(i == 1 ? '' : ', ', e[index]);
        }
      });
    }
  }
});