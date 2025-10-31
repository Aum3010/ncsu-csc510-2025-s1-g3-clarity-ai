/* global global */
import { describe, it, expect, vi, beforeEach } from "vitest";
import apiService from "../api-service.js";

// Mock SuperTokens functions
vi.mock("../supertokens-config.js", () => ({
  doesSessionExist: vi.fn(),
  getAccessToken: vi.fn(),
}));

// Mock fetch
global.fetch = vi.fn();

describe("API Service", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch.mockClear();
  });

  describe("validateSession", () => {
    it("should return true when session exists", async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockResolvedValue(true);

      const result = await apiService.validateSession();
      expect(result).toBe(true);
    });

    it("should return false when session does not exist", async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockResolvedValue(false);

      const result = await apiService.validateSession();
      expect(result).toBe(false);
    });

    it("should return false when session check throws error", async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockRejectedValue(new Error("Session check failed"));

      const result = await apiService.validateSession();
      expect(result).toBe(false);
    });
  });

  describe("getAuthHeaders", () => {
    it("should return auth headers when session is valid", async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockResolvedValue(true);

      const headers = await apiService.getAuthHeaders();

      // SuperTokens handles session tokens automatically, so we only expect Content-Type
      expect(headers).toEqual({
        "Content-Type": "application/json",
      });
    });

    it("should throw error when session is invalid", async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockResolvedValue(false);

      await expect(apiService.getAuthHeaders()).rejects.toThrow(
        "Authentication failed"
      );
    });
  });

  describe("makePublicRequest", () => {
    it("should make successful public API request", async () => {
      const mockResponse = { data: "test" };
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await apiService.makePublicRequest("core", "/test");

      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:5000/test",
        expect.objectContaining({
          headers: {
            "Content-Type": "application/json",
          },
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it("should handle API errors", async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: () => Promise.resolve({ message: "Resource not found" }),
      });

      await expect(
        apiService.makePublicRequest("core", "/test")
      ).rejects.toThrow("Resource not found");
    });
  });

  describe("Profile Management", () => {
    beforeEach(async () => {
      const { doesSessionExist } = await import("../supertokens-config.js");
      doesSessionExist.mockResolvedValue(true);
    });

    describe("getProfile", () => {
      it("should fetch user profile successfully", async () => {
        const { doesSessionExist } = await import("../supertokens-config.js");
        doesSessionExist.mockResolvedValue(true);

        const mockProfile = {
          user_id: "test-user",
          email: "test@example.com",
          metadata: {
            first_name: "Test",
            last_name: "User",
          },
        };

        global.fetch.mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockProfile),
        });

        const result = await apiService.getProfile("test-user");
        expect(result).toEqual(mockProfile);
      });

      it("should throw error when user ID is missing", async () => {
        await expect(apiService.getProfile()).rejects.toThrow();
      });
    });

    describe("updateProfile", () => {
      it("should update profile successfully", async () => {
        const { doesSessionExist } = await import("../supertokens-config.js");
        doesSessionExist.mockResolvedValue(true);

        const profileData = {
          metadata: {
            first_name: "Updated",
            last_name: "User",
            user_profile: {
              company: "Test Company",
              job_title: "Developer",
            },
          },
        };

        // Mock the GET request to check if profile exists
        global.fetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ user_id: "test-user" }),
        });

        // Mock the PUT request to update profile
        global.fetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(profileData),
        });

        const result = await apiService.updateProfile("test-user", profileData);
        expect(result).toEqual(profileData);
      });

      it("should validate required fields", async () => {
        const invalidData = {
          metadata: {
            first_name: "Test",
            // Missing required fields
          },
        };

        await expect(
          apiService.updateProfile("test-user", invalidData)
        ).rejects.toThrow("last name is required");
      });
    });

    describe("getProfileCompletionStatus", () => {
      it("should return complete status for complete profile", async () => {
        const { doesSessionExist } = await import("../supertokens-config.js");
        doesSessionExist.mockResolvedValue(true);

        const completeProfile = {
          metadata: {
            first_name: "Test",
            last_name: "User",
            user_profile: {
              company: "Test Company",
              job_title: "Developer",
            },
          },
        };

        global.fetch.mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(completeProfile),
        });

        const result = await apiService.getProfileCompletionStatus("test-user");

        expect(result.isComplete).toBe(true);
        expect(result.missingFields).toEqual([]);
      });

      it("should return incomplete status with missing fields", async () => {
        const { doesSessionExist } = await import("../supertokens-config.js");
        doesSessionExist.mockResolvedValue(true);

        const incompleteProfile = {
          metadata: {
            first_name: "Test",
            user_profile: {},
          },
        };

        global.fetch.mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(incompleteProfile),
        });

        const result = await apiService.getProfileCompletionStatus("test-user");

        expect(result.isComplete).toBe(false);
        expect(result.missingFields).toContain("last_name");
        expect(result.missingFields).toContain("company");
        expect(result.missingFields).toContain("job_title");
      });
    });
  });

  describe("Health Checks", () => {
    it("should perform health check successfully", async () => {
      const mockHealthResponse = { status: "ok" };
      global.fetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockHealthResponse),
      });

      const result = await apiService.healthCheck("core");

      expect(result.service).toBe("core");
      expect(result.status).toBe("ok");
      expect(result).toHaveProperty("timestamp");
    });

    it("should handle health check failures", async () => {
      global.fetch.mockRejectedValue(new Error("Network error"));

      const result = await apiService.healthCheck("core");

      expect(result.service).toBe("core");
      expect(result.status).toBe("unhealthy");
      expect(result.error).toBe("Network error");
    });
  });
});
