package com.georgernstgraf.aitranscribe.util

import android.content.Context
import com.arthenica.ffmpegkit.FFmpegKit
import com.arthenica.ffmpegkit.FFmpegKitConfig
import com.arthenica.ffmpegkit.FFprobeKit
import com.arthenica.ffmpegkit.FFprobeSession
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Utility class for chunking large audio files into smaller segments.
 * Ensures each chunk is under the specified max file size limit.
 *
 * @param context Application context for file operations
 * @param maxFileSizeMB Maximum file size in MB for each chunk (default: 25)
 */
@Singleton
class AudioChunker @Inject constructor(
    private val context: Context,
    private val maxFileSizeMB: Int = 25
) {

    companion object {
        private const val CHUNK_DURATION_SECONDS = 600 // 10 minutes per chunk
    }

    /**
     * Splits an audio file into chunks smaller than maxFileSizeMB.
     *
     * @param filePath Path to the audio file
     * @return List of chunk file paths (or single path if file is small enough)
     * @throws IllegalArgumentException if file doesn't exist
     * @throws Exception if chunking fails
     */
    suspend fun chunkAudio(filePath: String): List<String> = withContext(Dispatchers.IO) {
        val file = File(filePath)
        
        if (!file.exists()) {
            throw IllegalArgumentException("Audio file does not exist: $filePath")
        }

        val fileSizeMB = file.length() / (1024.0 * 1024.0)
        
        // If file is small enough, return original path
        if (fileSizeMB <= maxFileSizeMB) {
            return@withContext listOf(filePath)
        }

        // Get audio duration
        val duration = getAudioDuration(filePath)
        
        // Calculate number of chunks needed
        val chunkCount = calculateChunkCount(duration, fileSizeMB)
        
        // Create chunks
        val chunks = mutableListOf<String>()
        val chunkDuration = duration / chunkCount
        
        for (i in 0 until chunkCount) {
            val chunkPath = createChunkPath(file, i)
            val startTime = i * chunkDuration
            val endTime = if (i == chunkCount - 1) {
                duration // Last chunk goes to end
            } else {
                (i + 1) * chunkDuration
            }
            
            createChunk(
                inputPath = filePath,
                outputPath = chunkPath,
                startTime = startTime,
                endTime = endTime
            )
            
            chunks.add(chunkPath)
        }

        chunks
    }

    /**
     * Gets the duration of an audio file in seconds.
     *
     * @param filePath Path to the audio file
     * @return Duration in seconds
     * @throws Exception if unable to get duration
     */
    suspend fun getAudioDuration(filePath: String): Double = withContext(Dispatchers.IO) {
        val session: FFprobeSession = FFprobeKit.execute("-i \"$filePath\" -show_entries format=duration -v quiet -of csv=p=0")
        val output = session.output
        
        if (output.isNullOrEmpty()) {
            throw Exception("Unable to get audio duration")
        }
        
        try {
            output.trim().toDouble()
        } catch (e: NumberFormatException) {
            throw Exception("Invalid duration format: $output")
        }
    }

    /**
     * Calculates the number of chunks needed based on duration and file size.
     */
    private fun calculateChunkCount(duration: Double, fileSizeMB: Double): Int {
        // Start with 10-minute segments
        var chunkCount = (duration / CHUNK_DURATION_SECONDS).toInt().coerceAtLeast(1)
        
        // If chunks are still too large, increase count
        val estimatedChunkSize = fileSizeMB / chunkCount
        if (estimatedChunkSize > maxFileSizeMB) {
            chunkCount = (fileSizeMB / maxFileSizeMB).toInt() + 1
        }
        
        return chunkCount
    }

    /**
     * Creates a chunk file path.
     */
    private fun createChunkPath(originalFile: File, index: Int): String {
        val parentDir = originalFile.parent
        val baseName = originalFile.nameWithoutExtension
        val extension = originalFile.extension
        val uniqueId = UUID.randomUUID().toString().take(8)
        
        return "$parentDir/${baseName}_chunk${index}_$uniqueId.$extension"
    }

    /**
     * Creates a chunk using FFmpeg.
     */
    private suspend fun createChunk(
        inputPath: String,
        outputPath: String,
        startTime: Double,
        endTime: Double
    ) = withContext(Dispatchers.IO) {
        val duration = endTime - startTime
        val command = "-i \"$inputPath\" -ss $startTime -t $duration -c copy \"$outputPath\" -y"
        
        val session = FFmpegKit.execute(command)
        val returnCode = session.returnCode
        
        if (returnCode.isValueError) {
            throw Exception("Failed to create chunk: ${session.output}")
        }
    }
}