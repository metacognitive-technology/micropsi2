/*
 * viewer for the world.
 */

var canvas = $('#world');

var viewProperties = {
    frameWidth: 1445,
    zoomFactor: 1,
    objectWidth: 8,
    lineHeight: 15,
    objectLabelColor: new Color ("#94c2f5"),
    objectForegroundColor: new Color ("#000000"),
    fontSize: 10,
    symbolSize: 14,
    highlightColor: new Color ("#ffffff"),
    gateShadowColor: new Color("#888888"),
    shadowColor: new Color ("#000000"),
    shadowStrokeWidth: 0,
    shadowDisplacement: new Point(0.5,1.5),
    innerShadowDisplacement: new Point(0.2,0.7),
    hoverScale: 2,
    padding: 3,
    typeColors: {
        S: new Color('#009900'),
        U: new Color('#000099'),
        Tram: new Color('#990000'),
        Bus: new Color('#7000ff'),
        other: new Color('#304451')
    },
    label: {
        x: 10,
        y: -10
    }
};

objects = {};

currentWorld = $.cookie('selected_world') || null;

objectLayer = new Layer();
objectLayer.name = 'ObjectLayer';

objPrerenderLayer = new Layer();
objPrerenderLayer.name = 'PrerenderLayer';
objPrerenderLayer.visible = false;

var world_data = null;

refreshWorldList();
if (currentWorld){
    setCurrentWorld(currentWorld);
}
initializeControls();

function refreshWorldList(){
    $("#world_list").load("/world_list/"+(currentWorld || ''), function(data){
        $('#world_list .world_select').on('click', function(event){
            event.preventDefault();
            var el = $(event.target);
            var uid = el.attr('data');
            setCurrentWorld(uid);
        });
    });
}

function setCurrentWorld(uid){
    currentWorld = uid;
    // todo: get url from api.
    load_world_info();
    load_world_objects();
}

function load_world_info(){
    api('get_world_properties', {
        world_uid: currentWorld
    }, function(data){
        world_data = data;
        if('representation_2d' in data){
            view.viewSize = new Size(data['representation_2d']['x'], data['representation_2d']['y']);
            canvas.css('background', 'url("/static/img/'+ data['representation_2d']['image'] + '") no-repeat top left');
        }
    });
}

function load_world_objects(){
    api('get_world_objects', {world_uid: currentWorld}, function(data){
        $.cookie('selected_world', currentWorld, {expires:7, path:'/'});
        objectLayer.removeChildren();
        objects = {};
        for(var key in data){
            addObject(new WorldObject(data[key].uid, data[key].pos[0], data[key].pos[1], data[key].name, data[key].stationtype));
        }
        updateViewSize();
        refreshWorldList();
    });
}

function updateViewSize() {
    view.draw(true);
}


function WorldObject(uid, x, y, name, type){
    this.uid = uid;
    this.x = x;
    this.y = y;
    this.name = name;
    this.type = type;
    this.bounds = null;
}

function addObject(worldobject){
    if(! (worldobject.uid in objects)) {
        console.log('adding obejct: ' + worldobject.name);
        renderObject(worldobject);
        objects[worldobject.uid] = worldobject;
    }
    return worldobject;
}

function redrawObject(obj){
    objectLayer.children[obj.uid].remove();
    renderObject(obj);
}

function renderObject(worldobject){
    worldobject.bounds = calculateObjectBounds(worldobject);
    worldobject.representation = createStation(worldobject);
    objectLayer.addChild(worldobject.representation);
}

function calculateObjectBounds(worldobject){
    var width, height;
    width = height = viewProperties.objectWidth * viewProperties.zoomFactor;
    if (worldobject.type == "Tram"){
        width = height = 5;
    } else if (worldobject.type == 'other'  || worldobject.type == "Bus"){
        width = height = 3;
    }
    return new Rectangle(worldobject.x*viewProperties.zoomFactor - width/2,
        worldobject.y*viewProperties.zoomFactor - height/2, // center worldobject on origin
        width, height);
}

function createStation(worldobject){
    var bounds = worldobject.bounds;
    var shape = new Path.Circle(new Point(bounds.x + bounds.width/2, bounds.y+bounds.height/2), bounds.width/2);
    if(worldobject.type == "S" || worldobject.type == "S+U"){
        shape.fillColor = viewProperties.typeColors.S;
    } else {
        shape.fillColor = viewProperties.typeColors[worldobject.type];
    }
    return shape;
}

function api(functionname, params, success, error, method){
    var url = '/rpc/'+functionname;
    if(method != "post"){
        args = '';
        for(var key in params){
            args += key+'='+encodeURIComponent(JSON.stringify(params[key]))+',';
        }
        url += '('+args.substr(0, args.length-1) + ')';
    }
    $.ajax({
        url: url,
        data: ((method == "post") ? params : null),
        type: method || "get",
        success: function(data){
            if(data.Error){
                if(error) error(data);
                else defaultErrorCallback(data);
            } else{
                if(success) success(data);
                else defaultSuccessCallback(data);
            }
        },
        error: error || defaultErrorCallback
    });
}
function defaultSuccessCallback(data){
    dialogs.notification("Changes saved", 'success');
}
function defaultErrorCallback(data){
    dialogs.notification("Error: " + data.Error || "serverside exception", 'error');
}
function EmptyCallback(){}


function getLegend(worldobject){
    var legend = new Group();
    legend.name = 'stationLegend';
    var bounds = worldobject.bounds;
    var height = (viewProperties.fontSize*viewProperties.zoomFactor + 2*viewProperties.padding);
    var point = new Point(
        bounds.x + (viewProperties.label.x * viewProperties.zoomFactor),
        Math.max(height, bounds.y + (viewProperties.label.y * viewProperties.zoomFactor)));
    var text = new PointText(point);
    text.justification = 'left';
    text.content = (worldobject.name ? worldobject.name : worldobject.uid);
    text.characterStyle = {
        fillColor: 'black',
        fontSize: viewProperties.fontSize*viewProperties.zoomFactor
    };
    if(point.x + text.bounds.width + 2*viewProperties.padding > view.viewSize.width){
        point = new Point(
            view.viewSize.width - (text.bounds.width + 3*viewProperties.padding),
            point.y);
        text.point = point;
    }
    var container = new Path.Rectangle(new Point(point.x - viewProperties.padding, point.y + viewProperties.padding), new Size(text.bounds.width + 2*viewProperties.padding, -height));
    container.fillColor = 'white';
    legend.addChild(container);
    legend.addChild(text);
    return legend;
}

// -------------------------- mouse/ key listener --------------------------------------------//

hoverUid = false;
hoverPath = false;
path = false;
label = false;

function onMouseMove(event) {
    var p = event.point;
    // hovering
    if (hoverUid) { // unhover
        objects[hoverUid].representation.scale((1/viewProperties.hoverScale));
        hoverUid = null;
    }
    // first, check for nodes
    // we iterate over all bounding boxes, but should improve speed by maintaining an index
    for (var uid in objects) {
        var bounds = objects[uid].bounds;
        if (bounds.contains(p) && objects[uid].representation) {
            if (hoverUid != uid){
                hoverUid = uid;
                objects[uid].representation.scale(viewProperties.hoverScale);
                if (label){
                    label.remove();
                    label = null;
                }
                label = getLegend(objects[hoverUid]);
                objectLayer.addChild(label);
            }
            return;
        }
    }
    if (!hoverUid && label){
        label.remove();
        label = null;
    }
}


// --------------------------- controls -------------------------------------------------------- //

function initializeControls(){
    $('#world_start').on('click', startWorldrunner);
    $('#world_stop').on('click', stopWorldrunner);
}

function startWorldrunner(event){
    event.preventDefault();
    api('start_worldrunner', {world_uid: currentWorld});
}

function stopWorldrunner(event){
    event.preventDefault();
    api('stop_worldrunner', {world_uid: currentWorld});
}