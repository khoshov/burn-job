package ru.hackathon.profiling.sensorhub.web;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.NoHandlerFoundException;
import ru.hackathon.profiling.sensorhub.support.RequestContext;
import ru.hackathon.profiling.sensorhub.web.dto.ErrorDto;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorDto> handleApiException(ApiException ex) {
        ErrorDto dto = new ErrorDto(ex.getCode(), ex.getMessage(), RequestContext.getCorrelationId());
        return ResponseEntity.status(ex.getStatus()).body(dto);
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorDto> handleValidation(MethodArgumentNotValidException ex) {
        ErrorDto dto = new ErrorDto("VALIDATION_FAILED", "Validation failed: " + ex.getMessage(), RequestContext.getCorrelationId());
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(dto);
    }

    @ExceptionHandler(NoHandlerFoundException.class)
    public ResponseEntity<ErrorDto> handleNotFound(NoHandlerFoundException ex) {
        ErrorDto dto = new ErrorDto("NOT_FOUND", "Path not found", RequestContext.getCorrelationId());
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(dto);
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorDto> handleGeneral(Exception ex) {
        ErrorDto dto = new ErrorDto("INTERNAL_ERROR", ex.getMessage() != null ? ex.getMessage() : "Internal server error", RequestContext.getCorrelationId());
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(dto);
    }
}
