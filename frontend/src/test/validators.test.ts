import { describe, it, expect } from 'vitest'
import {
  EnvironmentConfigSchema,
  CircularObstacleSchema,
  RectangularObstacleSchema,
  GAPlanningParametersSchema,
} from '../utils/validators'

describe('Form and Parameter Validation', () => {
  it('validates a correct environment configuration', () => {
    const validConfig = {
      width: 100,
      height: 80,
      grid_resolution: 1.0,
      safety_clearance_m: 3.0,
      start_position: { x: 0, y: 0, z: 15 },
      destination: { x: 80, y: 60, z: 15 },
      monitoring_waypoints: [
        { id: 'WP_1', zone_name: 'Zone_A', priority: 1, x: 20, y: 20, z: 16 },
      ],
      obstacles: [
        { id: 'OBS_1', type: 'circle' as const, x: 10, y: 10, z: 15, radius: 2.0 },
      ],
      planning_params: {
        population_size: 100,
        max_generations: 80,
        crossover_probability: 0.85,
        mutation_probability: 0.15,
        two_opt_frequency: 5,
        two_opt_population_pct: 20,
        random_seed: 42,
      },
    }

    const res = EnvironmentConfigSchema.safeParse(validConfig)
    expect(res.success).toBe(true)
  })

  it('rejects an environment with negative map dimensions', () => {
    const invalidConfig = {
      width: -50,
      height: 80,
      grid_resolution: 1.0,
      safety_clearance_m: 3.0,
      start_position: { x: 0, y: 0, z: 15 },
      destination: { x: 80, y: 60, z: 15 },
      monitoring_waypoints: [
        { id: 'WP_1', zone_name: 'Zone_A', priority: 1, x: 20, y: 20, z: 16 },
      ],
      obstacles: [],
      planning_params: {
        population_size: 100,
        max_generations: 80,
        crossover_probability: 0.85,
        mutation_probability: 0.15,
        two_opt_frequency: 5,
        two_opt_population_pct: 20,
      },
    }

    const res = EnvironmentConfigSchema.safeParse(invalidConfig)
    expect(res.success).toBe(false)
  })

  it('rejects empty monitoring waypoints', () => {
    const invalidConfig = {
      width: 100,
      height: 80,
      grid_resolution: 1.0,
      safety_clearance_m: 3.0,
      start_position: { x: 0, y: 0, z: 15 },
      destination: { x: 80, y: 60, z: 15 },
      monitoring_waypoints: [], // Empty!
      obstacles: [],
      planning_params: {
        population_size: 100,
        max_generations: 80,
        crossover_probability: 0.85,
        mutation_probability: 0.15,
        two_opt_frequency: 5,
        two_opt_population_pct: 20,
      },
    }

    const res = EnvironmentConfigSchema.safeParse(invalidConfig)
    expect(res.success).toBe(false)
  })

  it('validates circular and rectangular obstacles', () => {
    const validCircle = {
      id: 'OBS_TREE',
      type: 'circle' as const,
      x: 15,
      y: 20,
      z: 16,
      radius: 2.5,
    }
    expect(CircularObstacleSchema.safeParse(validCircle).success).toBe(true)

    const invalidCircle = { ...validCircle, radius: -1 }
    expect(CircularObstacleSchema.safeParse(invalidCircle).success).toBe(false)

    const validRect = {
      id: 'OBS_RIDGE',
      type: 'rectangle' as const,
      min_x: 10,
      min_y: 15,
      max_x: 20,
      max_y: 25,
      z: 16,
    }
    expect(RectangularObstacleSchema.safeParse(validRect).success).toBe(true)

    const invertedRect = { ...validRect, min_x: 25, max_x: 10 }
    expect(RectangularObstacleSchema.safeParse(invertedRect).success).toBe(false)
  })

  it('validates GA crossover and mutation probabilities between 0 and 1', () => {
    const validParams = {
      population_size: 100,
      max_generations: 80,
      crossover_probability: 0.85,
      mutation_probability: 0.15,
      two_opt_frequency: 5,
      two_opt_population_pct: 20,
    }
    expect(GAPlanningParametersSchema.safeParse(validParams).success).toBe(true)

    const invalidParams = { ...validParams, crossover_probability: 1.5 }
    expect(GAPlanningParametersSchema.safeParse(invalidParams).success).toBe(false)
  })
})
