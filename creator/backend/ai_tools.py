"""Shared, versioned Morinote tool descriptions. All effects target an AI copy."""
def field(kind, description, required=False):
    return {'type':kind,'description':description,**({'required':True} if required else {})}

TOOLS = [
    {'name':'project','description':'Read the captured project, selection, stable scene/line IDs and source locations.','parameters':{}},
    {'name':'files','description':'List files in the task snapshot. Physical resources are read-only.','parameters':{}},
    {'name':'read','description':'Read one game text file with its current byte hash, BOM and line endings.','parameters':{'path':field('string','Project-relative game/... source path.',True)}},
    {'name':'write','description':'Create or replace one allowed game text file in the task copy. Never applies to the real project.','parameters':{'path':field('string','game/... path.',True),'content':field('string','Complete new source.',True),'hash':field('string','Expected hash from read; omit only for a new file.')}},
    {'name':'delete','description':'Delete one game text file in the copy. Human review is required before deleting the original.','parameters':{'path':field('string','game/... path.',True),'hash':field('string','Expected current hash.',True)}},
    {'name':'workspace','description':'Read original IDE configuration bindings, global story flow and three-track scene data, including Voice.','parameters':{}},
    {'name':'operate','description':'Edit using the original IDE adapters. operation.operation is mandatory. Examples for adapter=stage: text {operation:text,nodeId:LINE_ID,value:NEW_TEXT}; speaker {operation:speaker,nodeId:LINE_ID,value:ALIAS}; voice {operation:voice,nodeId:LINE_ID,asset:ASSET_ID}, omit asset to remove voice; image {operation:image,path:game/script.rpy,line:SHOW_OR_SCENE_LINE,value:actor smile}; audio {operation:audio,path:game/script.rpy,line:PLAY_LINE,property:volume,value:0.4}; properties {operation:properties,path:game/script.rpy,line:SHOW_LINE,values:{xpos:0.3,zoom:0.8}}; auto_wait {operation:auto_wait,nodeId:LINE_ID,value:2.0}; split_track {operation:split_track,nodeId:LINE_ID,track:visual_or_audio}. There is no actor or inherit_track operation; use image/properties, insert, remove, restore or source write. Lines refer to actual RPY statements, not dialogue anchors except nodeId. Config uses binding/value; flow uses node/operation/target; assets uses create/update/bind/unbind/delete. Hashes are filled by the host. Read workspace and source first.','parameters':{'adapter':{**field('string','IDE adapter.',True),'enum':['config','stage','flow','assets']},'operation':{**field('object','Original IDE operation object. Hash is supplied by the bridge.',True),'additionalProperties':True}}},
    {'name':'assets','description':'Read project-local virtual assets, missing requirements, substitutions, registered resources and references. Does not copy, replace or delete media.','parameters':{}},
    {'name':'analyze','description':'Rebuild the task source index. This is static analysis, not an engine test.','parameters':{}},
    {'name':'validate','description':'Validate task project references; reports actual diagnostics.','parameters':{}},
    {'name':'lint','description':'Run Ren’Py lint on this exact task version under DSH confinement. Fixed entry; no arbitrary shell command.','parameters':{}},
    {'name':'test','description':'Run only testsuite tests declared in this task. Returns not_run when none exist. Fixed Ren’Py test entry.','parameters':{}},
    {'name':'preview','description':'Start the real Ren’Py task-copy fragment under confinement, with isolated saves. Never launches the original project.','parameters':{'label':field('string','Existing fragment entry label.',True),'entry':{**field('object','Optional args array, state object, initialize labels.'),'additionalProperties':True}}},
    {'name':'preview_status','description':'Read task preview connection, current source, runtime state and events.','parameters':{'after':field('integer','Only events after this sequence.')}},
    {'name':'screenshot','description':'Capture the current task preview and return an image when the engine responds. Requires a running preview.','parameters':{}},
    {'name':'stop_preview','description':'Stop the task preview and its owned process tree.','parameters':{}},
    {'name':'read_image','description':'Read a registered task image, or @preview for the latest task screenshot.','parameters':{'path':field('string','game/... image path, or @preview.',True)}},
]

def catalog():
    return {'version':1,'scope':'task-copy','tools':TOOLS,'constraints':[
        'Only a human-reviewed IDE action can apply edits to original editor buffers.',
        'Do not fabricate manuscript confirmations, asset completion or mainline integration records.',
        'Check results carry a content hash and become stale when the snapshot changes.',
        'General terminal commands require individual host approval; no unrestricted fallback.',
    ]}
