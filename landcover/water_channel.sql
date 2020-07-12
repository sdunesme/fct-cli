#

WITH
tile AS (
    SELECT ST_SetSRID('BOX(1030000 6300000, 1040000 6310000)'::box2d, 2154) AS geom
),
water_channel AS (
    SELECT
        persistance,
        (ST_Dump(
            ST_Intersection(
                ST_Force2D(a.geom),
                (SELECT geom FROM tile)))).geom as geom
    FROM hydrographie.surface_hydrographique a
    WHERE ST_Intersects(a.geom, (SELECT geom FROM tile))
      AND persistance = 'Permanent'
)
SELECT DISTINCT persistance FROM water_channel
WHERE ST_GeometryType(geom) = 'ST_Polygon';