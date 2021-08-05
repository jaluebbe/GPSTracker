var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    this._div.innerHTML =
        '<div style="display: grid; grid-gap: 2px"><div>Choose data</div><div><select id="trackSelect">' +
        '<option selected value="artificial_tracking_data.json">artificial data</option>' +
        '<option value="real_tracking_data.json">real data</option>' +
        '<option value="airbus_tree.json">Airbus tree</option>' +
        '</select></div>' +
        '<div><input type="radio" id="showGpsAltitude" name="selectSource"><label for="showGpsAltitude">GPS altitude</label></div>' +
        '<div><input type="radio" id="showPressureAltitude" name="selectSource" checked><label for="showPressureAltitude">pressure altitude</label></div>'+
        '<div><label for="refPressureInput">p<sub>ref</sub> (mbar)</label>' +
        '<input type="number" id="refPressureInput" min="950" max="1050" value="1013.25" step="0.1"></div>' +
        '<div><button onclick="loadTrackingData();">load data</button></div></div>';
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
        '?show_gps_altitude=' + document.getElementById("showGpsAltitude").checked +
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

function refreshTrackingIndex() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', '../api/available_datasets?category=tracking');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        if (xhr.status === 200) {
            let trackSelect = document.getElementById('trackSelect');
            let len = trackSelect.options.length;
            for (var i=len; i; i--) {
                trackSelect.options.remove(i-1);
            }
            let trackingIndex = JSON.parse(xhr.responseText);
            trackingIndex.sort();
            for (var i=0; i < trackingIndex.length; i++) {
                let opt = document.createElement('option');
                opt.value = '../api/dataset/' + trackingIndex[i] + '.geojson';
                let keyItems = trackingIndex[i].split('_'); 
                opt.text = keyItems[1] + ' ' + keyItems[2];
                trackSelect.options.add(opt);
            }
        }
    };
    xhr.send();
}

refreshTrackingIndex();
function loadTrackingData() {
    loadGeoJSON(document.getElementById("trackSelect").value);
}
window.addEventListener('resize', adjustHeightgraphWidth);
