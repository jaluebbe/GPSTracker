const USE_GEOJSON = false;
var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    this._div.innerHTML =
        '<div style="display: grid; grid-gap: 2px"><div>Choose data</div><div><select id="trackSelect">' +
        '<optgroup label="Redis DB" id="redisOptions"></optgroup>' +
        '<optgroup label="Archive" id="archiveOptions"></optgroup>' +
        '</select></div>' +
        '<div><button onclick="loadTrackingData();">load data</button></div></div>';
    L.DomEvent.disableClickPropagation(this._div);
    return this._div;
};
legend.addTo(map);

var timeDimension = new L.TimeDimension({});
map.timeDimension = timeDimension;

var player = new L.TimeDimension.Player({
    transitionTime: 100,
    loop: false,
    startOver:true
}, timeDimension);

var timeDimensionControlOptions = {
    player: player,
    timeDimension: timeDimension,
    position: 'bottomleft',
    autoPlay: true,
    minSpeed: 1,
    speedStep: 1,
    maxSpeed: 60,
    timeSliderDragUpdate: true
};

var timeDimensionControl = new L.Control.TimeDimension(timeDimensionControlOptions);
map.addControl(timeDimensionControl);

var geoJSONLayer = L.geoJson([], {
    pointToLayer: function(feature, latLng) {
        if (feature.properties.hasOwnProperty('last')) {
            return new L.Marker(latLng, {});
        }
    }
}).addTo(map);

var geoJSONTDLayer = L.timeDimension.layer.geoJson(geoJSONLayer, {
    updateTimeDimension: true,
    updateTimeDimensionMode: 'replace',
    addlastPoint: true
}).addTo(map);

function loadJSON(fileName) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', fileName);
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.onload = function() {
        map.spin(false);
        if (xhr.status === 200) {
            var jsonData = JSON.parse(xhr.responseText);
            let geoJSONData = {
                "type": "Feature",
                "properties": {
                    "times": jsonData.map(item => {
                        return item.utc * 1e3;
                    })
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": jsonData.map(item => {
                        return [item.lon, item.lat];
                    })
                }
            };
            if (geoJSONData.properties.times.length > 0) {
                geoJSONLayer.clearLayers();
                geoJSONLayer.addData(geoJSONData);
                map.fitBounds(geoJSONLayer.getBounds());
            }
        }
    };
    map.spin(true);
    xhr.send();
}

function loadTrackingData() {
    loadJSON(document.getElementById("trackSelect").value);
}
