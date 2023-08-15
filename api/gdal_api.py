from osgeo import gdal
import aioredis
from fastapi import Request, APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, Response
import os
# from jinja2 import Environment, FileSystemLoader
import io
import mapscript
import xml.dom.minidom
import json
# import xarray as xr
import multiprocessing

router = APIRouter()

# Connect to Redis
async def connect_to_redis():
    global redis
    redis = aioredis.from_url(
        "redis://redis", encoding="utf-8", decode_responses=True
    )

# Startup event
@router.on_event('startup')
async def startup_event():
    await connect_to_redis()

# Shutdown event
@router.on_event('shutdown')
async def shutdown_event():
    redis.close()
    await redis.wait_closed()
    
    


def get_band_info(datasource, variable_name):
    nc_filename = '/app/data/S2B_MSIL1C_20230615T124709_N0509_R138_T28WFD_20230615T163218.nc'
    nc_url = 'https://nbstds.met.no/thredds/dodsC/NBS/S2B/2023/06/15/S2B_MSIL1C_20230615T124709_N0509_R138_T28WFD_20230615T163218.nc'
    datasource_id = 'S2B_MSIL1C_20230615T124709_N0509_R138_T28WFD_20230615T163218'
    sentinel_channles = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11', 'B12']
    s2b = {}
    dataset = gdal.Open('NETCDF:"{}":{}'.format(nc_filename, variable_name))
    # Get the geospatial transform (affine transformation coefficients)
    transform = dataset.GetGeoTransform()

    # Extract the extent from the geospatial transform
    xmin = transform[0]
    ymax = transform[3]
    xmax = xmin + transform[1] * dataset.RasterXSize
    ymin = ymax + transform[5] * dataset.RasterYSize
        
    # Get the minimum and maximum values
    band = dataset.GetRasterBand(1)  # Assuming you want to extract data range from the first band
    minimum = band.GetMinimum()
    maximum = band.GetMaximum()
    
    #xds = xr.open_dataset(nc_filename)
    #minimum, maximum = float(xds[variable_name].min()), float(xds[variable_name].max())

    # If the values are not set, calculate them
    #if minimum is None or maximum is None:
    #    minimum, maximum = band.ComputeRasterMinMax()
            
    # Get the projection
    projection = dataset.GetProjection()

    # Convert the projection to Proj4 string
    srs = gdal.osr.SpatialReference()
    srs.ImportFromWkt(projection)
    proj4_string = srs.ExportToProj4()
    # todo: build the vrt and add it to the dictionary
    opt = gdal.TranslateOptions(format='VRT', scaleParams=[[minimum, maximum]])
    ds = gdal.Translate(f'/app/data/{datasource}_{variable_name}_scaled.vrt', dataset, options=opt)
    dataset = None
    ds = None   
    # read the vrt file as a string and store it in the dictionary
    with open(f'/app/data/{datasource}_{variable_name}_scaled.vrt', 'r') as f:
        vrt_string = f.read()
    # build the dictionary
    variable_dict = {'datasource':datasource+'_'+variable_name,
                'extent':[int(xmin), int(ymin), int(xmax), int(ymax)],
                'proj4':proj4_string,
                'SRS': "EPSG:32628",
                'datarange':[minimum, maximum],
                'VRT':vrt_string}
    s2b[variable_name] = variable_dict
    return s2b




@router.get('/get_mapfile', response_class=Response)
async def get_mapfile(full_request: Request):
    # this returns the wms to a datasource
    # the datasource is a VRT file (or a list of them in a series of layers)
    # the VRT needs to be generated here
    # only once - meaning this method should:
    # 1. check if the VRT exists
    # 2. if not, generate it
    # 3. return the mapfile
    # once it generates the VRT, it should store it in redis
    # the VRT should be stored in redis as a string
    # the key should be the datasource name (preferably the datasource unic identifier)
    #print("Request url scheme:", full_request.url.scheme)
    #print("Request url netloc:", full_request.url.netloc)
    id = dict(full_request.query_params).get("id")
    layer = dict(full_request.query_params).get("LAYER")
    layers = dict(full_request.query_params).get("LAYERS")
    
    if id is None and layer is None and layers is None:
        raise HTTPException(status_code=404, detail="Missing required id or LAYER/s parameter")
    # check if the datasource exists in redis
    if id is None:
        try:
            id = layer.split('_')[0]
        except AttributeError:
            id = layers.split('_')[0]        
    value = await redis.get(id)
    # if the id is not found, generate the data and store it in redis
    # if the id is found, return the data from redis
    # the following routine is for sentinel 2 bands
    # the id in the case of sentinel 2 is the datasource id,
    # and can be used to retrieve the path to the resource on lustre.
    # otherwise we need toi full path to the resource on lustre as a url parameter
    # which will be thenm used to generate the VRT
    if value is None:
        sentinel_channles = ['B1', 
                             'B2', 
                             'B3', 
                             'B4', 
                             'B5', 
                             'B6', 
                             'B7', 
                             'B8', 
                             'B9', 
                             'B10', 
                             'B11', 
                             'B12']
        num_processes = multiprocessing.cpu_count()
        pool = multiprocessing.Pool(processes=num_processes)
        results = pool.starmap(get_band_info, zip([id] * len(sentinel_channles), sentinel_channles))
        pool.close()
        pool.join()
        print(results[0])
        #s2b = dict(results)
        s2b = {list(i.keys())[0]:i[list(i.keys())[0]] for i in results} 
        print("s2b:", s2b.keys())
        #s2b = get_info_s2b(id)
        
        async with redis.client() as conn:
            await conn.set(id, json.dumps(s2b))
    else:
        s2b = json.loads(value)

    netloc = os.environ.get("NETLOC_ADDRESS", full_request.url.netloc)
    scheme = os.environ.get("NETLOC_SCHEME", full_request.url.scheme)
    print("Using scheme:", scheme)
    print("Using netloc:", netloc)

    print(dict(full_request.query_params))
    # print("Request url path:", full_request.url.path)
    map_object = mapscript.mapObj()
    map_object.web.metadata.set( "wms_title", "GDAL Map Server" )
    map_object.web.metadata.set( "wms_abstract", "MapServer using GDAL" )
    map_object.web.metadata.set( "wms_enable_request", "*" )
    
    map_object.web.metadata.set( "wms_onlineresource", "http://0.0.0.0:8000/get_mapfile" )
    # map_object.web.metadata.set( "wcs_enable_request", "*" )
    # map_object.web.metadata.set( "wcs_onlineresource", "http://0.0.0.0:8000/get_mapfile" )
    # map_object.web.metadata.set( "wcs_srs", f"{s2b[list(s2b.keys())[0]].get('SRS')}" ) 
    #map_object.web.metadata.set( "wms_srs", "EPSG:32628" ) 
    map_object.web.metadata.set( "wms_srs", f"{s2b[list(s2b.keys())[0]].get('SRS')}" ) 
    map_object.setSize(800, 600)
    map_object.units = mapscript.MS_METERS
    
    # map_object.setProjection("+proj=utm +zone=28 +ellps=WGS84 +units=m +no_defs")
    map_object.setProjection(f"{s2b[list(s2b.keys())[0]].get('proj4')}")
    # take the extent from the first layer
    extent = s2b[list(s2b.keys())[0]].get('extent')
    map_object.setExtent(extent[0],extent[1],extent[2],extent[3])
    # map_object.setExtent(599995,7790225,709795,7900025)
    # check if vrt file exists, if not, create it
    for i in s2b:
        if f"{id}_{i}_scaled.vrt" not in os.listdir('/app/data'):
            with open(f"/app/data/{id}_{i}_scaled.vrt", 'w') as f:
                f.write(s2b[i].get('VRT'))
                print(f"Writing {id}_{i}_scaled.vrt")
        else:
            print(f"Found {id}_{i}_scaled.vrt")
            
    print("########  s2b key  ########")
    for i in s2b:
        print(i)
        layer = mapscript.layerObj()
        #layer.setProjection("+proj=utm +zone=28 +ellps=WGS84 +units=m +no_defs")
        layer.status = 1
        layer.data = f"/app/data/{id}_{i}_scaled.vrt"
        layer.type = mapscript.MS_LAYER_RASTER
        layer.name = f'{id}_{i}'
        layer.metadata.set("wms_title", f'{id}_{i}')
        extent = s2b[i].get('extent')
        layer.metadata.set("wms_extent", f"{' '.join(map(str, extent))}")
        layer.metadata.set("wms_srs", f"{s2b[i].get('SRS')}")
        # layer.metadata.set("wcs_extent", f"{' '.join(map(str, extent))}")
        # layer.metadata.set("wcs_srs", f"{s2b[i].get('SRS')}")
        # layer.metadata.set("wcs_formats", "GeoTIFF")
        # layer.metadata.set("wcs_label", f"Radiometry for band {i}") ### required
        
        #layer.metadata.set("wcs_rangeset_name", "Range 1")      ### required to support DescribeCoverage request
        # layer.metadata.set("wcs_rangeset_label", f"Band {i}")    ### required to support DescribeCoverage request
        #layer.metadata.set("wms_srs", "EPSG:32628")
        map_object.insertLayer(layer)

    map_object.save('test_gen_wcs.map')
    
    
    
    # map_object = mapscript.mapObj(file_object)

    ows_req = mapscript.OWSRequest()
    ows_req.type = mapscript.MS_GET_REQUEST
    print('full_request.query_params', full_request.query_params))   
    try:
        ows_req.loadParamsFromURL(str(full_request.query_params))
    except mapscript.MapServerError:
        ows_req = mapscript.OWSRequest()
        ows_req.type = mapscript.MS_GET_REQUEST
        pass
    if not full_request.query_params or ows_req.NumParams == 1:
        print("Query params are empty. Force getcapabilities")
        ows_req.setParameter("SERVICE", "WMS")
        ows_req.setParameter("VERSION", "1.3.0")
        ows_req.setParameter("REQUEST", "GetCapabilities")
    else:
        print("ALL query params: ", str(full_request.query_params))

    print("NumParams", ows_req.NumParams)
    print("TYPE", ows_req.type)
    if ows_req.getValueByName('REQUEST') != 'GetCapabilities':
        mapscript.msIO_installStdoutToBuffer()
        map_object.OWSDispatch( ows_req )
        content_type = mapscript.msIO_stripStdoutBufferContentType()
        result = mapscript.msIO_getStdoutBufferBytes()
    else:
        mapscript.msIO_installStdoutToBuffer()
        dispatch_status = map_object.OWSDispatch(ows_req)
        if dispatch_status != mapscript.MS_SUCCESS:
            print("DISPATCH status", dispatch_status)
        content_type = mapscript.msIO_stripStdoutBufferContentType()
        mapscript.msIO_stripStdoutBufferContentHeaders()
        _result = mapscript.msIO_getStdoutBufferBytes()
        print("content_type:", content_type)
        if content_type == 'application/vnd.ogc.wms_xml; charset=UTF-8':
            content_type = 'text/xml'
        dom = xml.dom.minidom.parseString(_result)
        result = dom.toprettyxml(indent="", newl="")
    return Response(result, media_type=content_type)
    
    