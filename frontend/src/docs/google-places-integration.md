# Google Places API Integration

This document explains how to use the enhanced Google Places API integration in the frontend application.

## Overview

The Google Places integration provides comprehensive place search, autocomplete, and detailed place information functionality. It includes rate limiting, error handling, and a rich user interface for business registration and management.

## Components

### 1. GooglePlacesService (`src/services/googlePlaces.ts`)

Core service that handles all Google Places API interactions:

```typescript
import { googlePlacesService } from '@/services/googlePlaces'

// Search for places
const results = await googlePlacesService.searchPlaces('restaurant near me')

// Get autocomplete predictions
const predictions = await googlePlacesService.getAutocompletePredictions('pizza')

// Get detailed place information
const details = await googlePlacesService.getPlaceDetails('ChIJ...')

// Generate photo URLs
const photoUrl = googlePlacesService.getPhotoUrl('photo_reference', {
  maxWidth: 400,
  maxHeight: 400
})
```

### 2. useGooglePlaces Composable (`src/composables/useGooglePlaces.ts`)

Vue composable for reactive Google Places functionality:

```vue
<script setup>
import { useGooglePlaces } from '@/composables/useGooglePlaces'

const {
  searchResults,
  autocompletePredictions,
  isLoading,
  error,
  searchPlaces,
  getAutocompletePredictions,
  getPlaceDetails
} = useGooglePlaces()

// Search for places
await searchPlaces('coffee shop')

// Get autocomplete predictions with debouncing
await debouncedAutocomplete('star')
</script>
```

### 3. GooglePlacesAutocomplete Component (`src/components/businesses/GooglePlacesAutocomplete.vue`)

Enhanced autocomplete input with rich place information:

```vue
<template>
  <GooglePlacesAutocomplete
    v-model="searchQuery"
    placeholder="Search for a business..."
    @place-selected="handlePlaceSelected"
    @prediction-selected="handlePredictionSelected"
    :types="['establishment']"
    :show-photos="true"
  />
</template>
```

### 4. PlaceDetailsModal Component (`src/components/businesses/PlaceDetailsModal.vue`)

Comprehensive place information display:

```vue
<template>
  <PlaceDetailsModal
    :place="selectedPlace"
    :loading="loading"
    :error="error"
    @close="closeModal"
    @select="selectPlace"
  />
</template>
```

## Configuration

### Environment Variables

Add your Google Places API key to the environment configuration:

```bash
# .env
VITE_GOOGLE_PLACES_API_KEY=your-google-places-api-key-here
```

### HTML Setup

The Google Places JavaScript SDK is loaded dynamically, but you can also include it in your HTML:

```html
<script>
  window.initGooglePlaces = function() {
    window.googlePlacesLoaded = true;
    window.dispatchEvent(new Event('google-places-loaded'));
  }
</script>
```

## Features

### Rate Limiting

The service includes built-in rate limiting:
- 10 requests per second
- 100 requests per minute
- Automatic request queuing
- Rate limit status monitoring

### Error Handling

Comprehensive error handling with user-friendly messages:
- API key validation
- Network error recovery
- Service initialization errors
- Rate limit exceeded warnings

### Photo Support

Rich photo integration:
- Automatic photo URL generation
- Multiple photo display
- Error handling for missing images
- Responsive image sizing

### Internationalization

Full i18n support:
- Multi-language place type formatting
- Localized error messages
- RTL language support
- Cultural formatting preferences

## Usage Examples

### Basic Place Search

```typescript
import { useGooglePlaces } from '@/composables/useGooglePlaces'

const { searchPlaces, searchResults, isLoading, error } = useGooglePlaces()

// Search for restaurants
await searchPlaces('restaurant', {
  location: { lat: 40.7128, lng: -74.0060 },
  radius: 5000,
  type: 'restaurant'
})

if (searchResults.value.length > 0) {
  console.log('Found restaurants:', searchResults.value)
}
```

### Autocomplete with Debouncing

```vue
<script setup>
import { ref, watch } from 'vue'
import { useGooglePlaces } from '@/composables/useGooglePlaces'

const searchQuery = ref('')
const { debouncedAutocomplete, autocompletePredictions } = useGooglePlaces()

watch(searchQuery, (newQuery) => {
  if (newQuery.length >= 2) {
    debouncedAutocomplete(newQuery, {
      types: ['establishment'],
      componentRestrictions: { country: 'us' }
    })
  }
})
</script>
```

### Place Details with Photos

```typescript
const { getPlaceDetails, getPhotoUrl } = useGooglePlaces()

const placeDetails = await getPlaceDetails('ChIJ...', [
  'name', 'formatted_address', 'photos', 'rating', 'reviews'
])

if (placeDetails?.photos) {
  const photoUrls = placeDetails.photos.map(photo => 
    getPhotoUrl(photo.photo_reference, { maxWidth: 800, maxHeight: 600 })
  )
}
```

## Best Practices

### Performance

1. **Use debouncing** for autocomplete to avoid excessive API calls
2. **Implement caching** for frequently accessed place details
3. **Optimize photo sizes** based on display requirements
4. **Monitor rate limits** to avoid service interruptions

### User Experience

1. **Show loading states** during API calls
2. **Handle errors gracefully** with user-friendly messages
3. **Provide fallback content** when photos are unavailable
4. **Use progressive enhancement** for better accessibility

### Security

1. **Restrict API keys** to specific domains and APIs
2. **Validate user inputs** before making API calls
3. **Implement proper CORS** configuration
4. **Monitor API usage** to detect abuse

## Troubleshooting

### Common Issues

1. **API Key Not Working**
   - Verify the API key is correctly set in environment variables
   - Check that the Places API is enabled in Google Cloud Console
   - Ensure domain restrictions are properly configured

2. **Rate Limit Exceeded**
   - Monitor the rate limit status using `getRateLimitStatus()`
   - Implement proper debouncing for user inputs
   - Consider caching frequently accessed data

3. **Photos Not Loading**
   - Check photo reference validity
   - Verify API key has photo access permissions
   - Implement proper error handling for missing images

4. **Autocomplete Not Working**
   - Ensure proper component restrictions are set
   - Check that the input meets minimum length requirements
   - Verify network connectivity and API availability

### Debug Mode

Enable debug logging by setting the log level in your environment:

```bash
VITE_LOG_LEVEL=debug
```

This will provide detailed information about API calls, rate limiting, and error conditions.