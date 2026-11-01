import { z } from 'zod'

export const Point3DSchema = z.object({
  x: z.number().finite('X must be a valid number'),
  y: z.number().finite('Y must be a valid number'),
  z: z.number().min(0, 'Altitude must be non-negative'),
})

export const MonitoringWaypointSchema = Point3DSchema.extend({
  id: z.string().min(1, 'Waypoint ID required'),
  zone_name: z.string().min(1, 'Zone name required'),
  priority: z.number().int().min(1).max(3),
})

export const CircularObstacleSchema = z.object({
  id: z.string().min(1, 'Obstacle ID required'),
  type: z.literal('circle'),
  x: z.number().finite(),
  y: z.number().finite(),
  z: z.number().min(0),
  radius: z.number().positive('Radius must be positive'),
})

export const RectangularObstacleSchema = z
  .object({
    id: z.string().min(1, 'Obstacle ID required'),
    type: z.literal('rectangle'),
    min_x: z.number().finite(),
    min_y: z.number().finite(),
    max_x: z.number().finite(),
    max_y: z.number().finite(),
    z: z.number().min(0),
  })
  .refine((data) => data.max_x > data.min_x, {
    message: 'Max X must be greater than Min X',
    path: ['max_x'],
  })
  .refine((data) => data.max_y > data.min_y, {
    message: 'Max Y must be greater than Min Y',
    path: ['max_y'],
  })

export const GAPlanningParametersSchema = z.object({
  population_size: z.number().int().min(10, 'Min population is 10').max(1000),
  max_generations: z.number().int().min(5, 'Min generations is 5').max(2000),
  crossover_probability: z.number().min(0, 'Crossover >= 0').max(1, 'Crossover <= 1'),
  mutation_probability: z.number().min(0, 'Mutation >= 0').max(1, 'Mutation <= 1'),
  two_opt_frequency: z.number().int().min(1, '2-Opt frequency >= 1'),
  two_opt_population_pct: z.number().min(0).max(100),
  random_seed: z.number().int().optional(),
})

export const EnvironmentConfigSchema = z.object({
  width: z.number().positive('Map width must be positive'),
  height: z.number().positive('Map height must be positive'),
  grid_resolution: z.number().positive('Grid resolution must be positive'),
  safety_clearance_m: z.number().min(0, 'Clearance must be non-negative'),
  start_position: Point3DSchema,
  destination: Point3DSchema,
  monitoring_waypoints: z.array(MonitoringWaypointSchema).min(1, 'At least 1 monitoring waypoint is required'),
  obstacles: z.array(z.union([CircularObstacleSchema, RectangularObstacleSchema])),
  planning_params: GAPlanningParametersSchema,
})
