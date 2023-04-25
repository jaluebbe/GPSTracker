const USE_GEOJSON = true;
const CATEGORY = "tracking";
var legend = L.control({
    position: 'topright'
});

function resetInputs() {
    refPressureInput.value = "1013.2";
    fromTimeInput.value = "";
    untilTimeInput.value = "";
};

legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    this._div.innerHTML =
        '<div style="display: grid; grid-gap: 2px">' +
        '<div>Choose data</div><div><select id="trackSelect" onchange="resetInputs();">' +
        '<optgroup label="Redis DB" id="redisOptions"></optgroup>' +
        '<optgroup label="Archive" id="archiveOptions"></optgroup>' +
        '</select></div>' +
        '<div><input type="radio" id="showGpsAltitude" name="selectSource">' +
        '<label for="showGpsAltitude">GPS altitude</label></div>' +
        '<div><input type="radio" id="showGebcoAltitude" name="selectSource">' +
        '<label for="showGebcoAltitude">GEBCO altitude</label></div>' +
        '<div><input type="radio" id="showPressureAltitude" name="selectSource" checked>' +
        '<label for="showPressureAltitude">pressure altitude</label></div>'+
        '<div class="two-columns">' +
        '<label for="refPressureInput">p<sub>ref</sub> (mbar)</label>' +
        '<input type="number" id="refPressureInput" min="950" max="1050" value="1013.2" step="0.1">' +
        '</div>' +
        '<div class="two-columns">' +
        '<label for="fromTimeInput">from</label><input type="time" id="fromTimeInput" step="1">' +
        '<label for="untilTimeInput">until</label><input type="time" id="untilTimeInput" step="1">' +
        '</div>' +
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
    let dateElements = trackSelect.value.match(/_(?<year>[\d]{4})(?<month>[\d]{2})(?<day>[\d]{2})\./).groups;
    let requestString = fileName +
        '&show_gps_altitude=' + showGpsAltitude.checked +
        '&show_gebco_altitude=' + showGebcoAltitude.checked +
        '&show_pressure_altitude=' + showPressureAltitude.checked +
        '&ref_pressure_mbar=' + refPressureInput.value;
    if (fromTimeInput.value.length > 0) {
        let fromTimeElements = fromTimeInput.value.split(":");
        let fromSeconds = 0;
        if (fromTimeElements.length > 2)
            fromSeconds = fromTimeElements[2];
        let fromDate = Date.UTC(dateElements.year, dateElements.month - 1, dateElements.day, fromTimeElements[0], fromTimeElements[1], fromSeconds);
        requestString = requestString + "&utc_min=" + fromDate / 1e3;}
    if (untilTimeInput.value.length > 0) {
        let untilTimeElements = untilTimeInput.value.split(":");
        let untilSeconds = 0;
        if (untilTimeElements.length > 2)
            untilSeconds = untilTimeElements[2];
        let untilDate = Date.UTC(dateElements.year, dateElements.month - 1, dateElements.day, untilTimeElements[0], untilTimeElements[1], untilSeconds);
        requestString = requestString + "&utc_max=" + untilDate / 1e3;
    }
    xhr.open('GET', requestString);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            if (document.getElementById("showGebcoAltitude").checked) {
                map.attributionControl.addAttribution('&copy <a href="https://www.gebco.net/data_and_products/gridded_bathymetry_data/gebco_2022/">GEBCO_2022 Grid</a>');
            }
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
    let dateElements = url.match(/_(?<year>[\d]{4})(?<month>[\d]{2})(?<day>[\d]{2})\./).groups;
    let requestString = url;
    if (fromTimeInput.value.length > 0) {
        let fromTimeElements = fromTimeInput.value.split(":");
        let fromSeconds = 0;
        if (fromTimeElements.length > 2)
            fromSeconds = fromTimeElements[2];
        let fromDate = Date.UTC(dateElements.year, dateElements.month - 1, dateElements.day, fromTimeElements[0], fromTimeElements[1], fromSeconds);
        requestString = requestString + "&utc_min=" + fromDate / 1e3;}
    if (untilTimeInput.value.length > 0) {
        let untilTimeElements = untilTimeInput.value.split(":");
        let untilSeconds = 0;
        if (untilTimeElements.length > 2)
            untilSeconds = untilTimeElements[2];
        let untilDate = Date.UTC(dateElements.year, dateElements.month - 1, dateElements.day, untilTimeElements[0], untilTimeElements[1], untilSeconds);
        requestString = requestString + "&utc_max=" + untilDate / 1e3;
    }
    let match = url.match(".*/(tracking.*.json)?.*$");
    if (match == null) {
        return;
    }
    let exportFileName = match[1];
    var xhr = new XMLHttpRequest();
    xhr.open('GET', requestString);
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
