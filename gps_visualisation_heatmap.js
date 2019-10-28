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
        '<option value="flightmap/static/airports_static.json">airports</option>' +
        '</select></td></tr>' +
        '</table>';
    L.DomEvent.on(div, 'click', function(ev) {
        L.DomEvent.stopPropagation(ev);
    });

    return div;
};
legend.addTo(map);
var locations = [];
var heatmap = L.heatLayer(locations, {
    minOpacity: 0.5,
    maxZoom: 18,
    max: 1.0,
    radius: 10,
    blur: 15,
    gradient: null
});
heatmap.addTo(map);

function loadGeoJSON(fileName) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', fileName);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        if (xhr.status === 200) {
            locations = [];
            let geojson = JSON.parse(xhr.responseText);
            if (Array.isArray(geojson)) {
                geojson = geojson[0]
            }
            geojson.features.forEach(function(feature) {
                if (feature.geometry.type == "LineString") {
                    feature.geometry.coordinates.forEach(function(location) {
                        let lastEntry = locations[locations.length - 1];
                        if (lastEntry != undefined && lastEntry[0] == location[1] && lastEntry[1] == location[0]) {
                            // remove consecutive duplicate coordinates
                            return;
                        }
                        locations.push([location[1], location[0]]);
                    })
                } else if (feature.geometry.type == "Point") {
                    let location = feature.geometry.coordinates;
                    locations.push([location[1], location[0]]);
                }
            });
            heatmap.setLatLngs(locations);
            map.fitBounds(L.latLngBounds(locations));
        }
    };
    xhr.send();
}
loadGeoJSON(document.getElementById("trackSelect").value);
document.getElementById("trackSelect").onchange = function() {
    loadGeoJSON(document.getElementById("trackSelect").value);
};
