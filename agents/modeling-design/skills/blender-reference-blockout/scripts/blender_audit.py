"""Read-only bpy audit. Send reviewed text through a permitted Blender bridge."""
import math


def bounds_from_points(points):
    points = [tuple(point) for point in points]
    if not points or any(len(p) != 3 or any(not math.isfinite(float(v)) for v in p) for p in points):
        raise ValueError('finite 3D points required')
    minimum = [min(p[i] for p in points) for i in range(3)]
    maximum = [max(p[i] for p in points) for i in range(3)]
    return {'min': minimum, 'max': maximum,
            'dimensions': [maximum[i] - minimum[i] for i in range(3)]}


def audit_blockout(collection_name, required_names=()):
    import bpy
    from mathutils import Vector

    collection = bpy.data.collections.get(collection_name)
    if collection is None:
        return {'status': 'missing_collection', 'collection': collection_name,
                'missing_components': list(required_names), 'objects': []}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = list(collection.all_objects)
    names = {obj.name for obj in objects}
    rows = []
    all_points = []
    for obj in objects:
        row = {'name': obj.name, 'type': obj.type,
               'hide_render': obj.hide_render,
               'modifiers': [{'type': modifier.type, 'name': modifier.name} for modifier in obj.modifiers]}
        if obj.type in ('MESH', 'CURVE', 'SURFACE', 'META', 'FONT'):
            evaluated = obj.evaluated_get(depsgraph)
            corners = [tuple(point) for point in evaluated.bound_box]
            # Blender uses all (-1,-1,-1) for unavailable bounding data.
            if corners and not all(point == (-1.0, -1.0, -1.0) for point in corners):
                points = [tuple(evaluated.matrix_world @ Vector(point)) for point in corners]
                row['world_bounds'] = bounds_from_points(points)
                all_points.extend(points)
            else:
                row['bounds_status'] = 'unavailable'
            row['measurement'] = 'evaluated_object_bbox_not_surface_collision'
        rows.append(row)
    return {'status': 'measured_not_accepted', 'collection': collection_name,
            'blender_version': bpy.app.version_string, 'file_path': bpy.data.filepath,
            'object_count': len(objects), 'missing_components': sorted(set(required_names) - names),
            'world_bounds': bounds_from_points(all_points) if all_points else None,
            'objects': rows, 'contact_review': 'not_checked', 'visual_review': 'not_checked',
            'instance_coverage': 'unrealized_instances_and_external_dependency_geometry_not_fully_audited',
            'claim_boundary': 'Read-only bounding evidence; no saves, geometry edits, full collision test or human approval.'}
