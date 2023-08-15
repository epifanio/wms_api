MAP
  NAME "GDAL Map"
  SIZE 800 600  # Adjust the size as per your requirements
  EXTENT {{ extent|join(' ') }}
  UNITS METERS
  # SHAPEPATH "/path/to/shapefiles"  # Set the path to your shapefiles directory

  PROJECTION
    "{{SRS}}"
  END

  WEB
    METADATA
      "wms_title" "GDAL Map Server"
      "wms_abstract" "MapServer using GDAL"
      "wms_enable_request" "*"
      "wms_onlineresource" "http://0.0.0.0:8000/get_mapfile"
    END
  END

  LAYER
    NAME "Raster Layer"
    TYPE RASTER
    DATA "/app/data/{{datasource}}"
    STATUS DEFAULT
    PROJECTION
      "{{SRS}}"
    END
  END
END