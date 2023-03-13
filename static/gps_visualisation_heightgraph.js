const USE_GEOJSON = true;
var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    this._div.innerHTML =
        '<div style="display: grid; grid-gap: 2px"><div>Choose data</div><div><select id="trackSelect">' +
        '<optgroup label="Redis DB" id="redisOptions"></optgroup>' +
        '<optgroup label="Archive" id="archiveOptions"></optgroup>' +
        '<optgroup label="Demo datasets" id="demoOptions">' +
        '<option selected value="artificial_tracking_data.json?">artificial data</option>' +
        '<option value="real_tracking_data.json?">real data</option>' +
        '<option value="airbus_tree.json?">Airbus tree</option>' +
        '</optgroup>' +
        '</select></div>' +
        '<div><input type="radio" id="showGpsAltitude" name="selectSource"><label for="showGpsAltitude">GPS altitude</label></div>' +
        '<div><input type="radio" id="showPressureAltitude" name="selectSource" checked><label for="showPressureAltitude">pressure altitude</label></div>'+
        '<div><label for="refPressureInput">p<sub>ref</sub> (mbar)</label>' +
        '<input type="number" id="refPressureInput" min="950" max="1050" value="1013.2" step="0.1"></div>' +
        '<div><button onclick="loadTrackingData();">load data</button></div>' +
        '<div><button onclick="exportTrackingData();">export as JSON</button></div></div>';
    L.DomEvent.disableClickPropagation(this._div);
    return this._div;
};
legend.addTo(map);
var hg;
function adjustHeightgraphWidth() {
    if (hg !== undefined) {
        hg.resize({
            width: window.innerWidth - 20
        });
    }
}
var geoJsonLayer = L.geoJson([]).addTo(map);
function loadGeoJSON(fileName) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', fileName +
        '&show_gps_altitude=' + document.getElementById("showGpsAltitude").checked +
        '&show_pressure_altitude=' + document.getElementById("showPressureAltitude").checked +
        '&ref_pressure_mbar=' + document.getElementById("refPressureInput").value);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            var geojson = JSON.parse(xhr.responseText);
            if (hg !== undefined)
                hg.remove();
            hg = L.control.heightgraph({
                width: window.innerWidth - 20,
                height: 180,
                margins: {
                    top: 10,
                    right: 30,
                    bottom: 55,
                    left: 50
                },
                expand: true,
                position: "bottomright"
            });
            hg.addTo(map);
            hg.addData(geojson);
            geoJsonLayer.clearLayers();
            if (geojson.length > 0) {
                geoJsonLayer.addData(geojson);
                map.fitBounds(geoJsonLayer.getBounds());
            }
        }
    };
    map.spin(true);
    xhr.send();
}
function loadTrackingData() {
    loadGeoJSON(document.getElementById("trackSelect").value);
}
function exportTrackingData() {
    let url = document.getElementById("trackSelect").value.replace(".geojson", ".json");
    let match = url.match(".*/(tracking.*.json)?.*$");
    if (match == null) {
        return;
    }
    let exportFileName = match[1];
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            var geojson = JSON.parse(xhr.responseText);
            let pom = document.createElement('a');
            pom.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(xhr.responseText));
            pom.setAttribute('download', exportFileName);
            if (document.createEvent) {
                let event = document.createEvent('MouseEvents');
                event.initEvent('click', true, true);
                pom.dispatchEvent(event);
            } else {
                pom.click();
            }
        }
    };
    map.spin(true);
    xhr.send();
}
window.addEventListener('resize', adjustHeightgraphWidth);
