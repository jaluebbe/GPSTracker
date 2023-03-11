map.createPane('boundaries');
map.createPane('plan');
map.createPane('protocol');
map.createPane('active');
map.createPane('vehicle');
map.getPane('boundaries').style.zIndex = 390;
map.getPane('plan').style.zIndex = 391;
map.getPane('protocol').style.zIndex = 392;
map.getPane('active').style.zIndex = 394;
map.getPane('vehicle').style.zIndex = 395;

function formatTooltip(content) {
    str = '<div class="tooltip-grid-container">';
    for (const key in content) {
        if (key == "V22RATE") {
            str = str + "<div>" + key + ":</div><div>" + (100 * content[key]).toFixed(0) + "&percnt;</div>";
        } else {
            str = str + "<div>" + key + ":</div><div>" + content[key] + "</div>";
        }
    }
    str = str + "</div>";
    return str;
}

function getDateString() {
    let date = new Date();
    return date.getFullYear() + "-" + (date.getMonth() + 1) + "-" + date.getDate() + "_" + date.getHours() + "-" + date.getMinutes();
}

function onEachFeature(feature, layer) {
    layer.bindTooltip(formatTooltip(feature.properties), {
        sticky: true,
        direction: "top",
        offset: [0, -5]
    });
}

function styleShape(feature, styleProperties) {
    return styleProperties;
}

var boundariesLayer = L.geoJSON([], {
    onEachFeature: onEachFeature,
    pane: 'boundaries',
    style: function(feature) {
        return styleShape(feature, {
            fillColor: "#003399",
            fillOpacity: 0.1,
            weight: 1.5,
            color: "blue"
        });
    }
}).addTo(map);
var planLayer = L.geoJSON([], {
    onEachFeature: onEachFeature,
    pane: 'plan',
    style: function(feature) {
        return styleShape(feature, {
            fillColor: "#ffcc00",
            fillOpacity: 0.15,
            weight: 1.5,
            color: "grey"
        });
    }
}).addTo(map);
var protocolLayer = L.geoJSON([], {
    onEachFeature: onEachFeature,
    pane: 'protocol',
    style: function(feature) {
        return styleShape(feature, {
            fillColor: "#00ee00",
            fillOpacity: feature.properties.coverage / 2,
            weight: 1.5,
            color: "grey"
        });
    }
}).addTo(map);
var boundariesLayerLabel = "<span style='background-color:rgba(0, 51, 153, 0.2)'>Boundaries</span>";
var planLayerLabel = "<span style='background-color:rgba(255, 204, 0, 0.2)'>Plan</span>";
var protocolLayerLabel = "<span style='background-color:rgba(0, 238, 0, 0.2)'>Protocol</span>";
layerControl.addOverlay(boundariesLayer, boundariesLayerLabel);
layerControl.addOverlay(planLayer, planLayerLabel);
layerControl.addOverlay(protocolLayer, protocolLayerLabel);
var settings = {};
var noSleep = new NoSleep();

function importProjectFileContent(fileContent) {
    let projectInput = JSON.parse(fileContent);
    boundariesLayer.addData(projectInput.boundaries);
    planLayer.addData(projectInput.plan);
    if (projectInput.protocol != null) {
        protocolLayer.addData(projectInput.protocol);
    }
    Object.assign(settings, projectInput.settings);
    if (boundariesLayer.getBounds().isValid())
        map.fitBounds(boundariesLayer.getBounds());
    else if (planLayer.getBounds().isValid())
        map.fitBounds(planLayer.getBounds());
};

function importProject() {
    let fileInput = dataTransferInputForm.fileInput;
    let storedData = sessionStorage.getItem('vigor22:project');
    if (fileInput.files.length == 0 && storedData == null) {
        return;
    }
    noSleep.enable();
    boundariesLayer.clearLayers();
    planLayer.clearLayers();
    protocolLayer.clearLayers();
    for (const key in settings) {
        delete settings[key];
    }
    for (var i = 0; i < fileInput.files.length; i++) {
        var fr = new FileReader();
        fr.onload = function(fileData) {
            importProjectFileContent(fileData.target.result);
        };
        fr.readAsText(fileInput.files[i])
    }
    if (fileInput.files.length == 0) {
        importProjectFileContent(storedData);
    }
    fileInput.value = "";
};

function exportProject() {
    exportName = "project";
    let fileName = prompt('Choose file name', exportName + '_' + getDateString() + '.json');
    if (fileName === null || fileName.length == 0) {
        return;
    }
    let dataExport = JSON.stringify({
        boundaries: boundariesLayer.toGeoJSON(),
        plan: planLayer.toGeoJSON(),
        protocol: protocolLayer.toGeoJSON(),
        settings: settings
    });
    sessionStorage.setItem('vigor22:project', dataExport);
    let pom = document.createElement('a');
    pom.setAttribute('href', 'data:application/json;charset=utf-8,' + encodeURIComponent(dataExport));
    pom.setAttribute('download', fileName);
    if (document.createEvent) {
        let event = document.createEvent('MouseEvents');
        event.initEvent('click', true, true);
        pom.dispatchEvent(event);
    } else {
        pom.click();
    }
};


var legend = L.control({
    position: 'topright'
});
legend.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info legend');
    let tempSource = document.getElementById('dataTransferInputTemplate');
    this._div.appendChild(tempSource.content.cloneNode(true));
    L.DomEvent.disableClickPropagation(this._div);
    return this._div;
}
legend.addTo(map);

var info = L.control({
    position: 'bottomright'
});
info.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info');
    this.showText('No geolocation information available.');
    return this._div;
};
info.showText = function(infoText) {
    this._div.innerHTML = infoText;
};
info.updateContent = function(heading, speed) {
    this._div.innerHTML = "<div style='text-align: left;'>heading:&nbsp;" + Math.round(heading * 100) / 100 +
        "&nbsp;deg<br>speed:&nbsp;" + Math.round(speed * 100) / 100 + "&nbsp;m/s</div>";
};
info.addTo(map);
var leftInfo = L.control({
    position: 'bottomleft'
});
leftInfo.onAdd = function(map) {
    this._div = L.DomUtil.create('div', 'info');
    return this._div;
};
leftInfo.showText = function(infoText) {
    this._div.innerHTML = infoText;
};
leftInfo.addTo(map);
var myMarker = L.marker([], {
    zIndexOffset: 1000
});
myMarker.bindTooltip("", {
    direction: 'top'
});
var myCircle = L.circle([], {
    radius: 0
});
var myPolyline = L.polyline([], {
    pane: 'vehicle',
    color: 'red'
});
var innerLeftPolygon = L.polygon([], {
    pane: 'active',
    color: 'green',
    fillOpacity: 0.3
});
var innerRightPolygon = L.polygon([], {
    pane: 'active',
    color: 'green',
    fillOpacity: 0.3
});
var outerLeftPolygon = L.polygon([], {
    pane: 'active',
    color: 'green',
    fillOpacity: 0.1
});
var outerRightPolygon = L.polygon([], {
    pane: 'active',
    color: 'green',
    fillOpacity: 0.1
});

var leftRate = 0;
var rightRate = 0;

function closeLeftShapes(outerLeftPoint, innerLeftPoint, centerPoint) {
    let timestamp = Date.now() / 1e3;
    if (!innerLeftPolygon.isEmpty()) {
        if (![innerLeftPoint, centerPoint].includes(undefined)) {
            extendShape(innerLeftPolygon, innerLeftPoint, centerPoint);
        }
        protocolLayer.addData(Object.assign(innerLeftPolygon.toGeoJSON(), {
            properties: {
                coverage: 0.7,
                rate: leftRate,
                timestamp: timestamp
            }
        }));
        innerLeftPolygon.setLatLngs([]);
    }
    if (!outerLeftPolygon.isEmpty()) {
        if (![outerLeftPoint, innerLeftPoint].includes(undefined)) {
            extendShape(outerLeftPolygon, outerLeftPoint, innerLeftPoint);
        }
        protocolLayer.addData(Object.assign(outerLeftPolygon.toGeoJSON(), {
            properties: {
                coverage: 0.3,
                rate: leftRate,
                timestamp: timestamp
            }
        }));
        outerLeftPolygon.setLatLngs([]);
    }
}

function closeRightShapes(outerRightPoint, innerRightPoint, centerPoint) {
    let timestamp = Date.now() / 1e3;
    if (!innerRightPolygon.isEmpty()) {
        if (![innerRightPoint, centerPoint].includes(undefined)) {
            extendShape(innerRightPolygon, innerRightPoint, centerPoint);
        }
        protocolLayer.addData(Object.assign(innerRightPolygon.toGeoJSON(), {
            properties: {
                coverage: 0.7,
                rate: rightRate,
                timestamp: timestamp
            }
        }));
        innerRightPolygon.setLatLngs([]);
    }
    if (!outerRightPolygon.isEmpty()) {
        if (![outerRightPoint, innerRightPoint].includes(undefined)) {
            extendShape(outerRightPolygon, outerRightPoint, innerRightPoint);
        }
        protocolLayer.addData(Object.assign(outerRightPolygon.toGeoJSON(), {
            properties: {
                coverage: 0.3,
                rate: rightRate,
                timestamp: timestamp
            }
        }));
        outerRightPolygon.setLatLngs([]);
    }
}

function extendShape(shape, firstPoint, secondPoint) {
    let points = shape.getLatLngs();
    points[0].push(firstPoint.geometry.coordinates.slice().reverse());
    points[0].unshift(secondPoint.geometry.coordinates.slice().reverse());
    shape.setLatLngs(points);
}

function onLocationFound(e) {
    console.log(e);
    myMarker.setLatLng(e.latlng);
    myCircle.setLatLng(e.latlng);
    myCircle.setRadius(e.accuracy);
    if (!map.hasLayer(myMarker)) {
        myMarker.addTo(map);
        myCircle.addTo(map);
        myPolyline.addTo(map);
        innerLeftPolygon.addTo(map);
        innerRightPolygon.addTo(map);
        outerLeftPolygon.addTo(map);
        outerRightPolygon.addTo(map);
    }
    if (!map.getBounds().contains(e.latlng)) {
        map.setView(e.latlng);
    }
    var centerPoint = turf.point([e.longitude, e.latitude]);
    if (typeof e.heading === "undefined") {
        info.showText('Speed and heading unavailable.');
        myPolyline.setLatLngs([]);
    } else if (e.speed < settings.min_speed) {
        myPolyline.setLatLngs([]);
        closeLeftShapes();
        closeRightShapes();
        leftRate = 0;
        rightRate = 0;
        info.showText('' + Math.round(e.speed * 100) / 100 + '&nbsp;m/s is too slow.<br>0%');
        leftInfo.showText('0%');
    } else {
        myMarker._tooltip.setContent('' + Math.round(e.speed * 100) / 100 + '&nbsp;m/s');
        let frontPoint = turf.destination(centerPoint, 5e-3, e.heading);
        let firstLeftQuartilePoint = turf.destination(centerPoint, settings.throwing_range * 0.25e-3, e.heading - 90);
        let firstRightQuartilePoint = turf.destination(centerPoint, settings.throwing_range * 0.25e-3, e.heading + 90);
        let thirdLeftQuartilePoint = turf.destination(centerPoint, settings.throwing_range * 0.75e-3, e.heading - 90);
        let thirdRightQuartilePoint = turf.destination(centerPoint, settings.throwing_range * 0.75e-3, e.heading + 90);
        let innerLeftPoint = turf.destination(centerPoint, settings.throwing_range * 0.5e-3, e.heading - 90);
        let innerRightPoint = turf.destination(centerPoint, settings.throwing_range * 0.5e-3, e.heading + 90);
        let outerLeftPoint = turf.destination(centerPoint, settings.throwing_range * 1e-3, e.heading - 90);
        let outerRightPoint = turf.destination(centerPoint, settings.throwing_range * 1e-3, e.heading + 90);
        myPolyline.setLatLngs([
            [centerPoint.geometry.coordinates.slice().reverse(),
                frontPoint.geometry.coordinates.slice().reverse()
            ],
            [centerPoint.geometry.coordinates.slice().reverse(),
                outerLeftPoint.geometry.coordinates.slice().reverse()
            ],
            [centerPoint.geometry.coordinates.slice().reverse(),
                outerRightPoint.geometry.coordinates.slice().reverse()
            ]
        ]);
        let firstLeftQuartileInBounds = false;
        let firstRightQuartileInBounds = false;
        let thirdLeftQuartileInBounds = false;
        let thirdRightQuartileInBounds = false;
        let outerLeftInBounds = false;
        let outerRightInBounds = false;
        let innerLeftInBounds = false;
        let innerRightInBounds = false;
        let centerInBounds = false;
        turf.featureEach(boundariesLayer.toGeoJSON(), function(feature, featureIndex) {
            firstLeftQuartileInBounds = firstLeftQuartileInBounds || turf.booleanPointInPolygon(firstLeftQuartilePoint, feature);
            firstRightQuartileInBounds = firstRightQuartileInBounds || turf.booleanPointInPolygon(firstRightQuartilePoint, feature);
            thirdLeftQuartileInBounds = thirdLeftQuartileInBounds || turf.booleanPointInPolygon(thirdLeftQuartilePoint, feature);
            thirdRightQuartileInBounds = thirdRightQuartileInBounds || turf.booleanPointInPolygon(thirdRightQuartilePoint, feature);
            outerLeftInBounds = outerLeftInBounds || turf.booleanPointInPolygon(outerLeftPoint, feature);
            outerRightInBounds = outerRightInBounds || turf.booleanPointInPolygon(outerRightPoint, feature);
            innerLeftInBounds = innerLeftInBounds || turf.booleanPointInPolygon(innerLeftPoint, feature);
            innerRightInBounds = innerRightInBounds || turf.booleanPointInPolygon(innerRightPoint, feature);
            centerInBounds = centerInBounds || turf.booleanPointInPolygon(centerPoint, feature);
        });
        let leftInBounds = outerLeftInBounds && innerLeftInBounds && firstLeftQuartileInBounds && thirdLeftQuartileInBounds;
        let rightInBounds = outerRightInBounds && innerRightInBounds && firstRightQuartileInBounds && thirdRightQuartileInBounds;
        let newLeftRate = 0;
        let newRightRate = 0;
        if (leftInBounds)
            newLeftRate = settings.default_rate;
        if (rightInBounds)
            newRightRate = settings.default_rate;
        turf.featureEach(planLayer.toGeoJSON(), function(feature, featureIndex) {
            if (leftInBounds && turf.booleanPointInPolygon(innerLeftPoint, feature)) {
                if (typeof feature.properties.V22RATE !== "undefined") {
                    newLeftRate = feature.properties.V22RATE;
                }
            }
            if (rightInBounds && turf.booleanPointInPolygon(innerRightPoint, feature)) {
                if (typeof feature.properties.V22RATE !== "undefined") {
                    newRightRate = feature.properties.V22RATE;
                }
            }
        });
        let leftCoverage = 0;
        let rightCoverage = 0;
        turf.featureEach(protocolLayer.toGeoJSON(), function(feature, featureIndex) {
            if (turf.booleanPointInPolygon(firstLeftQuartilePoint, feature)) {
                leftCoverage = leftCoverage + feature.properties.coverage;
            }
            if (turf.booleanPointInPolygon(firstRightQuartilePoint, feature)) {
                rightCoverage = rightCoverage + feature.properties.coverage;
            }
        });
        if (leftCoverage > 0.3) {
            newLeftRate = 0;
        }
        if (rightCoverage > 0.3) {
            newRightRate = 0;
        }
        info.showText(newRightRate * 1e2 + '%');
        leftInfo.showText(newLeftRate * 1e2 + '%');
        if (newLeftRate != leftRate) {
            closeLeftShapes(outerLeftPoint, innerLeftPoint, centerPoint);
            leftRate = newLeftRate;
        }
        if (newRightRate != rightRate) {
            closeRightShapes(outerRightPoint, innerRightPoint, centerPoint);
            rightRate = newRightRate;
        }
        if (newLeftRate > 0) {
            extendShape(innerLeftPolygon, innerLeftPoint, centerPoint);
            extendShape(outerLeftPolygon, outerLeftPoint, innerLeftPoint);
        }
        if (newRightRate > 0) {
            extendShape(innerRightPolygon, innerRightPoint, centerPoint);
            extendShape(outerRightPolygon, outerRightPoint, innerRightPoint);
        }
    }
}

dataTransferInputForm.fileInput.onchange = () => {
    importProject();
}

function onLocationError(e) {
    info.showText('No geolocation information available.');
}
map.setView([47.32, 8.2], 16);
