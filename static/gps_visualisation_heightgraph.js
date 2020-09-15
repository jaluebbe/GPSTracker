var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    var div = L.DomUtil.create('div', 'info legend');
    div.innerHTML =
        '<table><tr><td>Choose data</td></tr><tr><td><select id="trackSelect">' +
        '<option selected value="artificial_tracking_data.json">artificial data</option>' +
        '<option value="real_tracking_data.json">real data</option>' +
        '<option value="airbus_tree.json">Airbus tree</option>' +
        '</select></td></tr>' +
        '</table>';
    L.DomEvent.on(div, 'click', function(ev) {
        L.DomEvent.stopPropagation(ev);
    });

    return div;
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
    xhr.open('GET', fileName);
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
            geoJsonLayer.addData(geojson);
            map.fitBounds(geoJsonLayer.getBounds());
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
        loadGeoJSON(document.getElementById("trackSelect").value);
    };
    xhr.send();
}

refreshTrackingIndex();
document.getElementById("trackSelect").onchange = function() {
    loadGeoJSON(document.getElementById("trackSelect").value);
};
window.addEventListener('resize', adjustHeightgraphWidth);
