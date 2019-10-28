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
var hg = L.control.heightgraph({
    width: 480,
    height: 180,
    margins: {
        top: 10,
        right: 30,
        bottom: 55,
        left: 50
    },
    expand: false,
    position: "bottomright"
});
hg.addTo(map);
var geoJsonLayer = L.geoJson([]).addTo(map);

function loadGeoJSON(fileName) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', fileName);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        if (xhr.status === 200) {
            var geojson = JSON.parse(xhr.responseText);
            hg.addData(geojson);
            geoJsonLayer.clearLayers();
            geoJsonLayer.addData(geojson);
            map.fitBounds(geoJsonLayer.getBounds());
        }
    };
    xhr.send();
}
loadGeoJSON(document.getElementById("trackSelect").value);
hg._expand();
document.getElementById("trackSelect").onchange = function() {
    loadGeoJSON(document.getElementById("trackSelect").value);
};
