import { z } from 'zod';

/**
 * Order validation schemas for Extended Exchange
 * Ensures all orders are properly validated before submission
 */

export const orderFormSchema = z.object({
  market: z
    .string()
    .trim()
    .min(1, { message: 'Market is required' })
    .max(20, { message: 'Market name too long' })
    .regex(/^[A-Z0-9]+-[A-Z]+$/, { 
      message: 'Invalid market format (e.g., BTC-PERP, ETH-USD)' 
    }),
  
  side: z.enum(['BUY', 'SELL'], {
    errorMap: () => ({ message: 'Side must be BUY or SELL' }),
  }),
  
  price: z
    .string()
    .trim()
    .min(1, { message: 'Price is required' })
    .refine(
      (val) => {
        const num = parseFloat(val);
        return !isNaN(num) && num > 0 && num < 1_000_000_000;
      },
      { message: 'Price must be a positive number less than 1 billion' }
    ),
  
  size: z
    .string()
    .trim()
    .min(1, { message: 'Size is required' })
    .refine(
      (val) => {
        const num = parseFloat(val);
        return !isNaN(num) && num > 0 && num < 1_000_000;
      },
      { message: 'Size must be a positive number less than 1 million' }
    ),
  
  timeInForce: z.enum(['POST_ONLY', 'GTC', 'IOC', 'FOK'], {
    errorMap: () => ({ 
      message: 'Time in force must be POST_ONLY, GTC, IOC, or FOK' 
    }),
  }),
  
  reduceOnly: z.boolean(),
});

export type OrderFormData = z.infer<typeof orderFormSchema>;

/**
 * Validate and sanitize order form data
 */
export const validateOrderForm = (data: unknown): { 
  success: boolean; 
  data?: OrderFormData; 
  errors?: string[] 
} => {
  try {
    const validated = orderFormSchema.parse(data);
    return { success: true, data: validated };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors = error.errors.map(err => 
        `${err.path.join('.')}: ${err.message}`
      );
      return { success: false, errors };
    }
    return { success: false, errors: ['Unknown validation error'] };
  }
};
