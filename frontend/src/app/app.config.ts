import { ApplicationConfig } from '@angular/core';
import { provideHttpClient, withFetch } from '@angular/common/http';

// Configuration de l'application : fournit le client HTTP utilisé par les
// services pour dialoguer avec l'API backend.
export const appConfig: ApplicationConfig = {
  providers: [provideHttpClient(withFetch())],
};
